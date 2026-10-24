# Progress

Last updated: 2026-10-25

**Status key**
- **Written:** files exist but have not been run or confirmed by you.
- **Verified:** you ran it and shared the real output (or the result is directly observable in the project folder or Git log).

The short "state and exact next step" note is in `HANDOFF.md`.

## Current status

Phase 0 is complete. The Phase 1 setup files and a first version of the decision engine (roadmap Phases 2 and 3, minus the "Why not X?" comparison) plus the FastAPI backend are **verified by automated tests**: 83 tests pass and `ruff` reports no problems (run by you on 2026-10-25, recorded in `docs/TESTING.md`). Not yet verified: the server running in a browser, and anything about the frontend, which has not been started. The earlier "Written" labels in the tables below mean the same files, now covered by that test run.

## Completed work

| Item | Status | Notes |
|---|---|---|
| Filesystem access to `E:\apps and codes j\WhatIf2.0` | Verified | `filesystem_test.txt` was written and read back through the filesystem integration. Kept for now. |
| `PROJECT_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `.gitignore`, `.env.example` | Written | Revised after the consistency review and again on 2026-10-25 to match the master specification. |
| First commit: "Add project foundation and documentation" | Verified | Seen in the Git log. |
| Second commit: "Refine documentation after consistency review" | Verified | Seen in the Git log. |
| `backend/pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `app/__init__.py`, `tests/test_smoke.py`, `README.md` | Written | Phase 1 step 1 files. Not run. |
| `docs/SCORING_MODEL.md` | Written | Math and worked laptop example, calculated by hand. |
| `docs/DECISIONS.md` | Written | D-001 to D-010. |
| `CHANGELOG.md`, `HANDOFF.md` | Written | |
| Engine: `models.py`, `validation.py`, `normalize.py`, `constraints.py`, `scoring.py`, `explain.py`, `__init__.py` | Written | Standard library only. Hard constraints, eligible-only normalization, stable tie handling, templated explanations. Not run. |
| Engine tests: `tests/engine/test_normalize.py`, `test_validation.py`, `test_scoring.py`, `test_explain.py`, plus `tests/helpers.py` | Written | Expected numbers come from the hand calculation, including the constraint case (A = 0.6, C = 0.4), equal-weights tie, scale invariance, and the weight-driven ranking reversal. Not run. |

## Added later in the same session (all Written, not run)

| Item | Notes |
|---|---|
| `backend/app/main.py`, `config.py`, `api/schemas.py`, `api/converters.py`, `api/routes.py` | FastAPI app with `GET /api/health`, `POST /api/analyze`, `GET /api/templates`, `GET /api/templates/{id}`. Pydantic limits mirror the engine. CORS restricted to configured origins. 256 KB declared-size limit. |
| `backend/app/templates/*.json` | Three illustrative templates (laptop, study priorities, project prioritization). Weights and criteria only. |
| `backend/tests/api/test_api.py` | Reference example through the API, constraint reasons, 422 cases, size limit, CORS, templates. |
| `requirements.txt`, `requirements-dev.txt` | fastapi, uvicorn, pytest, ruff, httpx. Unpinned until a real install works. |
| `scripts/setup-backend.cmd`, `scripts/run-backend.cmd` | One-step setup, test and lint; start the server on 127.0.0.1. |

## Observations about the folder

- `filesystem_test.txt` is still present. If it was committed, remove it later with `git rm` once you decide it is no longer needed.
- The project path contains spaces. Quote it in terminal commands.
- Uncommitted: documentation edits and everything marked Written above since the second commit. Do not commit until pytest and ruff have been run.

## Blockers

None.

## Next exact action

Commit the verified work and scaffold the frontend (commands in `HANDOFF.md`).

## Implementation roadmap

Each phase ends with working, tested software before the next begins. The decision-tree builder, soft preferences, and Science Fest evaluation plan from the master specification are placed in Phases 11 and 12 (D-001).

| Phase | Goal | Status |
|---|---|---|
| 0 | Planning and documentation | Done |
| 1 | Toolchain check, backend skeleton, minimal README | **Verified** (tests and ruff pass; versions confirmed) |
| 2 | Core engine: models, validation, normalization, weighted-sum scoring, ranking | **Verified** by automated tests against hand calculations |
| 3 | Constraints, ties, explanation data, and "Why not X?" comparison | Constraints, ties, explanations written. "Why not X?" not started |
| 4 | API: `/api/health` and `/api/analyze` (and templates endpoints) | **Verified** by API tests. Not yet tried by hand at http://127.0.0.1:8000/docs |
| 5 | Frontend skeleton and first vertical slice: input form, call API, ranking, contribution chart, normalized values | Not started |
| 6 | Sensitivity: weight sweep, switching points, seeded rank-stability simulation | Not started |
| 7 | Scenarios (weights, values, thresholds, option availability) | Not started |
| 8 | Templates | Three written (backend only), no UI yet |
| 9 | Decision journal with SQLite and outcome reviews | Not started |
| 10 | Exports: JSON, CSV (formula-safe), printable report | Not started |
| 11 | Optional AI-assisted parsing (provider-independent, fake-provider tests) and decision tree builder | Not started |
| 12 | Polish, accessibility, soft preferences, final README, demo script, Science Fest evaluation plan, full manual checklist | Not started |

## Decisions log

Full reasoning is in `docs/DECISIONS.md`.

| Date | Decision | Status |
|---|---|---|
| 2026-10-25 | Documentation first, before any application code | Agreed |
| 2026-10-25 | Keep `filesystem_test.txt` for now | Agreed |
| 2026-10-25 | Stack: Next.js, FastAPI, SQLite, local run for the demo | Specified by master prompt |
| 2026-10-25 | D-002: normalize over eligible options only | Decided |
| 2026-10-25 | D-003: scenarios may override weights, values, thresholds, availability | Decided |
| 2026-10-25 | D-005: missing values rejected | Decided |
| 2026-10-25 | D-006: engine uses only the standard library | Decided |
| 2026-10-25 | Journal storage through built-in `sqlite3` | Proposed, confirm at Phase 9 |
| 2026-10-25 | Tailwind and Recharts | Confirm at Phase 5 |

## Session notes

- 2026-10-25 (earlier): Created the planning documents and configuration files, then the consistency review and Phase 1 step 1 files.
- 2026-10-25 (this session): Inspected the folder against the master specification. Resolved conflicts (scenario scope, decision-tree builder, soft preferences, AI provider, missing handoff, decisions, and changelog files, normalization scope). Wrote the scoring model document, the engine, and the engine tests. Nothing was run.
