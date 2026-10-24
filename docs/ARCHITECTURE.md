# Architecture

Status: **proposed**, except the engine (`backend/app/engine/`), which is written but not yet run. See `docs/SCORING_MODEL.md` and `docs/DECISIONS.md`. Choices marked "confirm at scaffolding" are expected to be finalized when that part is first set up.

## 1. Goals that shaped the design

- A beginner can understand, run, and debug the whole system.
- Costs nothing to run, test, or demo.
- The decision math is isolated, deterministic, and easy to test.
- Works fully offline on one laptop (the most dependable setup for a live demo).
- AI is optional and cannot affect correctness of results.

Toolchain as reported by the project owner (not independently checked): Python 3.13.14, Node.js 24.22.1, npm 11.19.1, Git 2.56.0, on Windows with VS Code. Phase 1 confirms these on the real machine, and library versions are chosen to match them.

## 2. Overview

Two small programs on one machine, plus a SQLite file.

```
 Browser (Next.js UI, port 3000)
        |
        |  JSON over HTTP
        v
 FastAPI backend (port 8000)
   |-- api/        request/response handling and validation
   |-- engine/     pure decision math (no web, no database, no AI)
   |-- storage/    SQLite access for the journal
   |-- ai/         optional text-to-structure parser (feature flag)
        |
        v
 SQLite file (local journal)
```

### Why this split

- The **engine** is the heart of the product and is ordinary Python functions. It can be tested with `pytest` without starting a server, which is the easiest kind of test to learn on.
- The **API layer** is thin: validate input, call the engine, return the result.
- The **frontend** collects input and presents results. It does not recompute scores, so there is one source of truth for the numbers.

## 3. Planned directory layout

Created incrementally, not all at once.

```
WhatIf2.0/
  PROJECT_GUIDE.md
  README.md                  (started in Phase 1; how to install and run)
  .gitignore
  .env.example
  docs/
    ARCHITECTURE.md
    TESTING.md
    progress.md
  backend/
    pyproject.toml           pytest and ruff settings
    requirements.txt
    requirements-dev.txt
    app/
      main.py                app creation, CORS, router registration
      config.py              reads environment variables
      api/                   route modules (analyze, templates, journal, ai)
      engine/
        models.py            input and result data structures
        validation.py        domain rules beyond type checks
        normalize.py         min-max normalization
        scoring.py           weighted sum, ranking, ties
        constraints.py       hard-limit filtering with reasons
        sensitivity.py       weight sweeps, switching points, simulation
        explain.py           templated plain-language explanations
      storage/               database setup and journal queries
      ai/                    optional parser, prompt, response validation
      templates/             decision templates as JSON files
    tests/
      engine/
      api/
      storage/
      ai/
  frontend/
    package.json
    src/
      app/                   pages (start, new decision, results, journal, report)
      components/            forms, tables, charts
      lib/                   API client, types, export helpers
```

## 4. Data flow

### Analyzing a decision

1. The user builds a decision in the UI (options, criteria, weights, values, constraints).
2. The frontend does light checks (required fields, numeric input) and sends `POST /api/analyze` with the decision model as JSON.
3. The backend validates the payload (types, ranges, size limits, domain rules).
4. The engine normalizes values, applies constraints, scores, ranks, and builds the explanation data.
5. The backend returns the result as JSON.
6. The frontend renders the ranking, contribution charts, and explanation.

Analysis is **stateless**: nothing is saved unless the user chooses to save to the journal.

### Saving to the journal

1. The user clicks Save. The frontend sends the model, a result snapshot, and the user's reasoning to the journal endpoint.
2. The backend validates and stores them in SQLite.
3. Later, the user opens the entry and records the option they chose and an outcome review.

### Optional AI parsing

1. The user pastes text and explicitly clicks "Parse".
2. The backend checks the feature flag and input length, then sends the text to the AI provider.
3. The response is parsed and **validated against the same schema as manual input**.
4. The frontend shows the proposed structure in the normal editable form. Nothing is analyzed until the user confirms.

### Exports

JSON and CSV exports are produced in the browser from the data already on screen, so they need no backend endpoint. The printable report is a frontend page the user prints or saves as PDF through the browser.

## 5. The decision model and engine behavior

### Input model (conceptual)

- `options`: list of names.
- `criteria`: each has a name, a direction (`benefit` or `cost`), a raw importance weight, and an optional unit.
- `values`: one number per option per criterion. Qualitative factors are entered as numeric ratings on a user-chosen scale. Missing values are rejected in the first version.
- `constraints`: each refers to one criterion with `<=` or `>=` and a threshold on the raw value.
- `scenarios` (later): named copies of the model with overrides of weights, values, constraint thresholds, or option availability (D-003). The engine stays stateless.
- `schema_version`: so saved decisions can be migrated when the model changes.

### Calculations

- **Weights:** raw weights are rescaled to sum to 1. All-zero weights are rejected.
- **Normalization (min-max), per criterion:**
  - benefit: `(x - min) / (max - min)`
  - cost: `(max - x) / (max - min)`
  - If every option has the same value (`max == min`), the criterion cannot separate options, so every option gets the same normalized value (proposed 0.5). Covered by a test.
- **Score:** `sum(weight_i * normalized_value_i)`, a value between 0 and 1.
- **Constraints:** an option violating any constraint is marked ineligible, with the violated rule recorded. Ineligible options are shown but not ranked.
- **Ranking:** descending score. Scores within a small tolerance (proposed `1e-9`) are treated as a tie and share a rank. Ties are flagged in the result.
- **Contribution breakdown:** `weight_i * normalized_value_i` per option per criterion. These sum exactly to the score, which is what makes the charts honest.
- **One-at-a-time sensitivity:** vary one criterion's weight from 0 to 1 while rescaling the other weights in proportion. Because each score is a linear function of that one weight, switching points between two options can be solved exactly instead of estimated by trial. If every other weight is zero there is nothing to rescale, so that criterion's sweep is reported as not defined rather than guessed.
- **Rank stability simulation:** repeatedly perturb every weight by a random factor within a user-chosen percentage (for example plus or minus 25%), renormalize, rerank, and count how often each option ranks first. Uses a recorded seed so a run can be reproduced. When several options tie for first in one run, they split that run's credit equally, so shares always sum to 100%. This reports the share of *simulated weightings*, not a probability that the user is "right".
- **Explanations:** produced from templates filled with the real numbers (for example the largest contributing criteria, the margin over the runner-up, the nearest switching point). No AI text in this path.

### Known limitations

These belong in the product's own wording as well as here.

- **Scores are relative.** Min-max results depend on which options were entered. Adding or removing an option can change scores and, in some cases, the order of the remaining options (rank reversal). A score of 0.6 is not an absolute rating.
- **Outliers compress the rest.** One extreme value on a criterion squeezes the normalized values of all other options toward each other.
- **Linear trade-offs.** Weighted sum assumes that more of a benefit is always proportionally better and that criteria can be traded off against each other. Criteria with a best value in the middle are not supported in the first version.
- **Weights are judgments.** Sensitivity analysis shows how much the weights matter. It cannot say whether they are right.

## 6. API sketch (proposed)

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Confirm the backend is running |
| `POST /api/analyze` | Score and rank a decision model |
| `POST /api/sensitivity` | Weight sweeps, switching points, simulation |
| `GET /api/templates` and `GET /api/templates/{id}` | List and fetch templates |
| `POST /api/journal/decisions` | Save a decision |
| `GET /api/journal/decisions` and `GET /api/journal/decisions/{id}` | Browse and open entries |
| `PUT /api/journal/decisions/{id}` | Edit reasoning or chosen option |
| `POST /api/journal/decisions/{id}/review` | Record an outcome review |
| `DELETE /api/journal/decisions/{id}` | Delete an entry |
| `POST /api/ai/parse` | Optional text-to-structure parsing (feature flag) |

FastAPI also generates interactive API docs, which are handy for manual testing while learning.

## 7. Storage

- **SQLite** through Python's built-in `sqlite3` module with parameterized queries (confirm at Phase 9). One file, no server, no cost, and no extra dependency. There is a single table, so an ORM such as SQLAlchemy is not justified unless the schema grows.
- A `decisions` table holds: id, title, created and updated times, the decision model as a JSON text column, a result snapshot as JSON, chosen option, reasoning, review outcome, review notes, review time.
- Storing the model as JSON keeps the schema small and flexible. The trade-off is that you cannot query inside it, so search covers title and notes only.
- Database creation is automatic on first run, and the file is excluded from Git.
- The database path is resolved relative to the backend folder, not the terminal's current folder, so the file does not end up in different places depending on where the server was started.

## 8. Proposed limits (enforced by the backend)

Initial values, adjustable after testing:

- Options per decision: at most 20
- Criteria per decision: at most 15
- Names: at most 100 characters; free-text notes: at most 2,000 characters
- Numeric values: finite numbers only (no NaN or infinity), with absolute value at most 1e12 to avoid overflow and precision loss
- Raw weights: between 0 and 1,000
- Simulation runs: at most 10,000 (default 1,000). Weight sweep steps: at most 200
- Request body: about 256 KB. Uvicorn does not enforce a body size by default. The field limits above bound the size in practice, and a small size check is added in Phase 4 if testing shows it is needed.
- AI input: `AI_MAX_INPUT_CHARS` (default 4,000)

## 9. Frontend notes (confirm at scaffolding)

- Next.js App Router with TypeScript strict mode.
- State in plain React state and context. No heavy state library.
- Charts with Recharts. Styling with Tailwind CSS, which the Next.js setup offers as an option.
- A thin API client in `lib/api.ts`. Response types are written by hand at first.
- Browser-to-API calls: either direct calls (needs CORS configured) or a Next.js rewrite that forwards `/api/*` to the backend (same origin, avoids most CORS problems). Decide in Phase 5.
- Guided input in steps (options, criteria and weights, values, limits), since a wizard is easier for first-time users than one large form.

## 10. Trade-offs and alternatives considered

| Decision | Chosen | Alternative | Reason and cost |
|---|---|---|---|
| Languages | Python backend, TypeScript frontend | Everything in TypeScript | The brief names both stacks, and a Python engine is easy to unit test. Cost: two runtimes, two sets of tools, more to learn. A TypeScript-only app would be simpler to deploy. Keeping the engine free of web code makes a later port feasible. |
| Where math runs | Backend only | Duplicate in browser | One source of truth for numbers. Cost: the UI needs the backend running, even for simple analysis. |
| Scoring method | Weighted sum first | TOPSIS, AHP, outranking methods | Easiest to explain to a first-time user. Cost: assumes criteria trade off linearly. More methods can be added after the first is solid. |
| Normalization | Decided (D-002): min-max over eligible options only | The other one | Over all options: scores do not shift when a constraint is toggled, but a ruled-out option still stretches the scale. Over eligible options: a ruled-out option behaves as if it was never entered, which is easier to explain, but scores change when a constraint is toggled. |
| Database | SQLite via built-in `sqlite3` | PostgreSQL, a hosted service, or SQLite with an ORM | Zero cost, zero setup, no extra dependency. Cost: not suited to many simultaneous users, and hand-written queries need care (parameters only). |
| Accounts | None in v1 | Login system | Large security and maintenance burden for a demo. Cost: no public multi-user hosting (see open decisions). |
| Explanations | Templated from numbers | AI-written | Reproducible, testable, free. Cost: less fluent prose. |
| AI | Optional, off by default | Core feature | The product must be correct and usable without it. Also avoids a paid dependency. |
| Python packaging | `venv` and `requirements.txt` | Poetry or uv | Fewest concepts for a beginner. Cost: less sophisticated dependency handling. |
| Shared types | Hand-written TypeScript types | Generated from FastAPI's OpenAPI schema | Simpler to start. Cost: the two sides can drift. Generation can be added later. |
| Run model | Local on one laptop | Hosted | Most dependable for a live demo and free. Cost: visitors cannot use it on their own phones unless hosting is added later. |

## 11. Open decisions

1. **Public hosting and storage.** If the app is ever hosted for many people, how is the journal kept private? Options include per-browser storage, accounts, or no journal on the public version.
2. **Project path.** Keep `E:\apps and codes j\WhatIf2.0` (spaces in the path) or move to a path without spaces if tools misbehave.
3. **Normalization scope: resolved (D-002).** Eligible options only. The expected numbers for this case are in `docs/SCORING_MODEL.md` section 3. Toggling a constraint changes the scores of the remaining options, and the product must say so.
4. **Styling.** Confirm Tailwind versus plain CSS at frontend scaffolding.
5. **AI in the demo.** Whether to include AI parsing at all, which provider, and who pays for API usage. API usage is billed separately from a Claude chat plan; check current pricing before deciding.
6. **Tie tolerance and simulation defaults.** Settle after testing.
7. **Repository visibility and license.** Whether the repository will be public (for example on GitHub). This affects the license choice and how carefully secrets and personal data must be kept out of the history.

## 12. Demo considerations (Science Fest)

- Run everything locally. Do not depend on venue Wi-Fi for core features.
- Ship one or two ready templates and a saved example journal entry so the demo starts from a good state.
- Use a fixed simulation seed so the demo shows repeatable results.
- Keep a JSON export of the demo decisions as a restore point.
- Leave AI parsing off unless it has been tested with a working key and a graceful failure message.
- Visitors may type real personal decisions. Use a separate demo database that is reset between visitors, ask visitors not to enter personal details, and never demo from your own journal.
- Start the backend bound to `127.0.0.1` so other devices on the venue network cannot reach it.
