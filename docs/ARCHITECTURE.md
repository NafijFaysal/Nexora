# Architecture

Status: **proposed**. Nothing here has been built or run yet. Choices marked "confirm at scaffolding" are expected to be finalized when that part is first set up.

## 1. Goals that shaped the design

- A beginner can understand, run, and debug the whole system.
- Costs nothing to run, test, or demo.
- The decision math is isolated, deterministic, and easy to test.
- Works fully offline on one laptop (the most dependable setup for a live demo).
- AI is optional and cannot affect correctness of results.

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
  README.md                  (later: how to install and run)
  .gitignore
  .env.example
  docs/
    ARCHITECTURE.md
    TESTING.md
    progress.md
  backend/
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
- `values`: one number per option per criterion. Missing values are rejected in the first version.
- `constraints`: each refers to one criterion with `<=` or `>=` and a threshold on the raw value.
- `scenarios` (later): named overrides of weights.
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
- **One-at-a-time sensitivity:** vary one criterion's weight from 0 to 1 while rescaling the other weights in proportion. Because each score is a linear function of that one weight, switching points between two options can be solved exactly instead of estimated by trial.
- **Rank stability simulation:** repeatedly perturb every weight by a random factor within a user-chosen percentage (for example plus or minus 25%), renormalize, rerank, and count how often each option ranks first. Uses a recorded seed so a run can be reproduced. This reports the share of *simulated weightings*, not a probability that the user is "right".
- **Explanations:** produced from templates filled with the real numbers (for example the largest contributing criteria, the margin over the runner-up, the nearest switching point). No AI text in this path.

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

- **SQLite** through SQLAlchemy (confirm at scaffolding). One file, no server, no cost.
- A `decisions` table holds: id, title, created and updated times, the decision model as a JSON text column, a result snapshot as JSON, chosen option, reasoning, review outcome, review notes, review time.
- Storing the model as JSON keeps the schema small and flexible. The trade-off is that you cannot query inside it, so search covers title and notes only.
- Database creation is automatic on first run, and the file is excluded from Git.

## 8. Proposed limits (enforced by the backend)

Initial values, adjustable after testing:

- Options per decision: at most 20
- Criteria per decision: at most 15
- Names: at most 100 characters; free-text notes: at most 2,000 characters
- Numeric values: finite numbers only (no NaN or infinity)
- Request body: about 256 KB
- AI input: `AI_MAX_INPUT_CHARS` (default 4,000)

## 9. Frontend notes (confirm at scaffolding)

- Next.js App Router with TypeScript strict mode.
- State in plain React state and context. No heavy state library.
- Charts with Recharts. Styling with Tailwind CSS, which the Next.js setup offers as an option.
- A thin API client in `lib/api.ts`. Response types are written by hand at first.
- Guided input in steps (options, criteria and weights, values, limits), since a wizard is easier for first-time users than one large form.

## 10. Trade-offs and alternatives considered

| Decision | Chosen | Alternative | Reason and cost |
|---|---|---|---|
| Languages | Python backend, TypeScript frontend | Everything in TypeScript | The brief names both stacks, and a Python engine is easy to unit test. Cost: two runtimes, two sets of tools, more to learn. A TypeScript-only app would be simpler to deploy. Keeping the engine free of web code makes a later port feasible. |
| Where math runs | Backend only | Duplicate in browser | One source of truth for numbers. Cost: the UI needs the backend running, even for simple analysis. |
| Scoring method | Weighted sum first | TOPSIS, AHP, outranking methods | Easiest to explain to a first-time user. Cost: assumes criteria trade off linearly. More methods can be added after the first is solid. |
| Normalization | Min-max over all entered options | Over eligible options only | Scores do not shift when a constraint is toggled. Cost: results depend on which options were entered. Revisit after seeing real examples. |
| Database | SQLite | PostgreSQL or a hosted service | Zero cost and zero setup. Cost: not suited to many simultaneous users. |
| Accounts | None in v1 | Login system | Large security and maintenance burden for a demo. Cost: no public multi-user hosting (see open decisions). |
| Explanations | Templated from numbers | AI-written | Reproducible, testable, free. Cost: less fluent prose. |
| AI | Optional, off by default | Core feature | The product must be correct and usable without it. Also avoids a paid dependency. |
| Python packaging | `venv` and `requirements.txt` | Poetry or uv | Fewest concepts for a beginner. Cost: less sophisticated dependency handling. |
| Shared types | Hand-written TypeScript types | Generated from FastAPI's OpenAPI schema | Simpler to start. Cost: the two sides can drift. Generation can be added later. |
| Run model | Local on one laptop | Hosted | Most dependable for a live demo and free. Cost: visitors cannot use it on their own phones unless hosting is added later. |

## 11. Open decisions

1. **Public hosting and storage.** If the app is ever hosted for many people, how is the journal kept private? Options include per-browser storage, accounts, or no journal on the public version.
2. **Project path.** Keep `E:\apps and codes j\WhatIf2.0` (spaces in the path) or move to a path without spaces if tools misbehave.
3. **Normalization scope.** Confirm "all entered options" after seeing results on real examples.
4. **Styling.** Confirm Tailwind versus plain CSS at frontend scaffolding.
5. **AI in the demo.** Whether to include AI parsing at all, which provider, and who pays for API usage. API usage is billed separately from a Claude chat plan; check current pricing before deciding.
6. **Tie tolerance and simulation defaults.** Settle after testing.

## 12. Demo considerations (Science Fest)

- Run everything locally. Do not depend on venue Wi-Fi for core features.
- Ship one or two ready templates and a saved example journal entry so the demo starts from a good state.
- Use a fixed simulation seed so the demo shows repeatable results.
- Keep a JSON export of the demo decisions as a restore point.
- Leave AI parsing off unless it has been tested with a working key and a graceful failure message.
