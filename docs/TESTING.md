# Testing Plan

Status: **planned only**. No application code exists yet, no tests have been written, and no test has been run. Results are recorded in section 7 only after you run the tests and share the output.

## 1. Approach

- **Test the math first and hardest.** The engine is pure Python, so it can be tested quickly and without a server.
- **Hand-calculate before coding.** For every calculation feature, work out an expected answer on paper (see section 3) and use it as a test. A test that only repeats the code's own output proves nothing.
- **Tests are part of the feature.** A feature is not done without them (see the definition of done in `PROJECT_GUIDE.md`).
- **No real AI calls in automated tests.** The AI module is tested with a fake provider, so tests are free, fast, and repeatable.
- **Compare floats with tolerance**, for example `pytest.approx`.

## 2. Tools (planned)

| Layer | Tool | Purpose |
|---|---|---|
| Backend unit and API tests | `pytest`, FastAPI `TestClient` | Engine, endpoints, storage |
| Backend lint and format | `ruff` | Consistent, clean Python |
| Frontend component tests | Vitest and React Testing Library | Forms, tables, result display |
| Frontend lint and types | ESLint, `tsc` (type check) | Catch mistakes early |
| End-to-end (optional, later) | Playwright | Full user flows in a real browser |

Exact commands will be added here when each tool is first set up and confirmed to work on your machine. Expected form, from the backend folder with the virtual environment active (to be confirmed):

```
python -m pytest
python -m ruff check .
```

and from the frontend folder:

```
npm run lint
npm test
```

Remember to quote the project path in PowerShell because it contains spaces.

## 3. Hand-calculated reference example

This fixture should be encoded as tests as soon as the scoring engine exists. All figures below were worked out by hand and have **not** yet been checked by running code.

**Decision:** choose a laptop.

| Option | Price (cost) | Quality rating (benefit) |
|---|---|---|
| A | 800 | 7 |
| B | 1000 | 9 |
| C | 600 | 5 |

Raw weights: price 4, quality 6 (rescaled to 0.4 and 0.6).

**Normalization (min-max):**

- Price is a cost: `(1000 - x) / 400` gives A = 0.5, B = 0, C = 1.
- Quality is a benefit: `(x - 5) / 4` gives A = 0.5, B = 1, C = 0.

**Contributions and scores:**

| Option | Price contribution | Quality contribution | Score |
|---|---|---|---|
| A | 0.4 x 0.5 = 0.20 | 0.6 x 0.5 = 0.30 | 0.50 |
| B | 0.4 x 0 = 0.00 | 0.6 x 1 = 0.60 | 0.60 |
| C | 0.4 x 1 = 0.40 | 0.6 x 0 = 0.00 | 0.40 |

**Expected ranking:** B (0.6), A (0.5), C (0.4).

**Derived expectations to test:**

- **Scale invariance:** raw weights 40 and 60, or 2 and 3, must give the same result.
- **Constraint:** `price <= 900` makes B ineligible. Scores stay A = 0.5 and C = 0.4 (normalization uses all entered options), so ranking is A first, C second, B listed as ineligible with the reason.
- **Tie:** with equal weights (0.5 each), every option scores 0.5, so all three tie at rank 1 and the result flags a tie.
- **Sensitivity on the price weight `w`** (quality weight `1 - w`): A = 0.5 for every `w`, B = `1 - w`, C = `w`. The top option changes from B to C at `w = 0.5`. At exactly 0.5 all three tie. Option A never wins outright. This is a useful check that the switching-point calculation finds `0.5`.
- **Contribution sums:** for every option, contributions add up to the score.

## 4. Planned automated tests

### 4.1 Engine: validation

- Fewer than 2 options is rejected; more than the maximum is rejected.
- No criteria is rejected.
- Duplicate option names or duplicate criterion names are rejected.
- Negative weights are rejected; all-zero weights are rejected.
- Missing values, NaN, and infinity are rejected.
- Constraints that refer to an unknown criterion are rejected.
- Over-long names or notes are rejected.

### 4.2 Engine: normalization

- Benefit and cost direction on the reference example.
- All options equal on a criterion (the `max == min` case).
- Negative values and decimals.
- Very large and very small numbers do not break the calculation.
- The result for each option stays between 0 and 1.

### 4.3 Engine: scoring and ranking

- Reference example scores and ranking.
- Scale invariance of weights.
- Ties share a rank and are flagged.
- Contributions sum to the score.
- Result does not change when options are entered in a different order.

### 4.4 Engine: constraints

- `<=` and `>=` behavior, including a value exactly equal to the threshold.
- Multiple constraints on one option, with all violated rules reported.
- All options ineligible gives a clear result, not a crash.
- Ineligible options appear in results but are not ranked.

### 4.5 Engine: sensitivity and simulation

- Weight sweep: scores at `w = 0`, `0.5`, and `1` match hand calculations.
- Switching point on the reference example is `0.5`.
- A decision with no switching point reports that clearly.
- Simulation with the same seed gives identical results; a different seed may differ.
- Simulation with 0% variation reproduces the base ranking in every run.
- Simulation shares across options sum to 100%.

### 4.6 Engine: explanations

- Explanation text names the correct top option and its biggest contributing criteria.
- Margin and runner-up figures match the computed scores.
- Tie and ineligible cases produce sensible wording.

### 4.7 API

- `GET /api/health` returns success.
- `POST /api/analyze` returns the expected result for the reference example.
- Invalid payloads return a clear error and never a server crash.
- Oversized payloads are rejected.
- CORS allows the configured origin and rejects others.

### 4.8 Storage and journal

- Save, list, open, edit, review, and delete an entry (using a temporary test database, never the real one).
- Saved JSON loads back identical to what was stored.
- Opening a missing entry returns a clear not-found error.
- Text containing quotes and unusual characters is stored and returned safely.

### 4.9 Templates

- Every template file parses and passes validation.
- Template weights are valid.

### 4.10 AI parsing (fake provider only)

- Well-formed response is accepted and converted.
- Malformed, partial, or off-schema responses are rejected without a crash.
- Responses containing instructions or odd content are treated as data and validated like any other input.
- Disabled feature flag returns a clear "not enabled" error.
- Input over the length limit is rejected before any call.

### 4.11 Frontend

- Input forms: adding and removing options and criteria, validation messages.
- Results view renders ranking, contributions, and ineligible reasons from a fixed sample result.
- Export helpers produce correct JSON and CSV for a sample result, including values with commas and quotes.
- Chart components render with and without data.

### 4.12 End-to-end (later, optional)

- Start from a template, fill in values, see a ranking, change a weight, see the result update.
- Save to the journal, reload the page, reopen the entry.
- Export and re-import a decision model and get the same result.

## 5. Manual verification checklist

Run before any demo or release, and after major changes.

**Setup**

- [ ] Fresh clone or clean folder: follow the README steps exactly and confirm the app starts. (Catches missing steps.)
- [ ] Backend health endpoint responds in the browser.
- [ ] Frontend loads without errors in the browser console.

**Core flow**

- [ ] Enter the reference laptop example by hand. Ranking is B, A, C with scores 0.6, 0.5, 0.4.
- [ ] Add the constraint `price <= 900`. B shows as ineligible with a clear reason.
- [ ] Set equal weights. The tie is visible and explained.
- [ ] Try bad input (empty names, text in number fields, a huge number). Messages are clear and nothing crashes.

**Explainability**

- [ ] The explanation text agrees with the numbers in the table and chart.
- [ ] Sensitivity chart shows the switch at 0.5 for the reference example.
- [ ] Rank-stability results are the same on repeated runs with the same seed.

**Journal and exports**

- [ ] Save, close the browser, reopen, and find the entry.
- [ ] Record an outcome review and see it displayed.
- [ ] JSON export re-imports to the same result.
- [ ] CSV opens in a spreadsheet with correct columns.
- [ ] Print preview of the report is readable on one or two pages.

**Usability and accessibility**

- [ ] Complete a decision using the keyboard only.
- [ ] Text is readable at 200% zoom.
- [ ] Charts have labels or a text summary, and color is not the only signal.
- [ ] A first-time person can finish the sample decision without help. (Informal observation only; do not present this as a study.)

**Privacy and security**

- [ ] `git status` shows no `.env` or database file staged.
- [ ] Search the repository for key-like strings before pushing anywhere.
- [ ] With AI off, no network request to an AI provider is made.

## 6. When a test fails

1. Copy the full error output.
2. Decide whether the test or the code is wrong, using the hand calculation as the arbiter.
3. Fix the cause, not the symptom. Do not loosen a test just to make it pass.
4. Add a regression test if the bug was not already covered.

## 7. Verification record

Fill this in only from real output you have run and shared.

| Date | What was run | Result | Notes |
|---|---|---|---|
| (none yet) | | | |
