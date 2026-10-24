# Progress

Last updated: 2026-10-25

**Status key**
- **Written:** files exist but have not been run or confirmed by you.
- **Verified:** you ran it and shared the real output (or the result is directly observable in the project folder).

## Current status

Phase 0 (planning and documentation) is complete, apart from committing the review corrections made on 2026-10-25. No application code exists. No command has been run by Claude, no dependency installed, no application started, and no test executed.

## Completed work

| Item | Status | Notes |
|---|---|---|
| Filesystem access to `E:\apps and codes j\WhatIf2.0` | Verified | `filesystem_test.txt` was written and read back through the filesystem integration. The file is kept for now, as requested. |
| `PROJECT_GUIDE.md` | Written | Vision, users, principles, features, standards, security, workflow. Revised after the consistency review. |
| `docs/ARCHITECTURE.md` | Written | Proposed design, data flow, trade-offs, open decisions. Revised after the review. |
| `docs/TESTING.md` | Written | Test plan and a hand-calculated reference example. No tests exist yet. Revised after the review. |
| `docs/progress.md` | Written | This file. |
| `.gitignore` | Written | Python, Node.js, Next.js, env files, databases (including SQLite sidecar files), editor files. |
| `.env.example` | Written | Placeholders only. |
| Consistency review of the four documents | Written | Corrections listed in the session notes below. |
| First Git commit | Verified | The Git log shows one commit on `main`: "Add project foundation and documentation". |

## Observations about the folder

- The Git log has one commit. Claude did not check whether it includes the review corrections (it does not, since they were made afterwards) or `filesystem_test.txt`. If `filesystem_test.txt` was committed, remove it later with `git rm` once you decide it is no longer needed.
- The project path contains spaces. Quote it in terminal commands. See `PROJECT_GUIDE.md`, section 8.

## Blockers

None. One decision is needed before Phase 3 (not before): normalization scope, open decision 3 in `docs/ARCHITECTURE.md`.

## Next exact action

1. Commit the review corrections. From the project folder in the VS Code terminal, run `git status`, check that only the expected files are listed (`PROJECT_GUIDE.md`, `.gitignore`, `.env.example`, and the three files in `docs/`), and paste the output to Claude. If it looks right, then:
   ```
   git add .
   git commit -m "Refine documentation after consistency review"
   ```
2. Tell Claude to start **Phase 1, step 1** (below).

### Phase 1, step 1: toolchain check and backend skeleton

Goal: prove the Python environment, `pytest`, and `ruff` work on your machine before any real code is written.

Files Claude will create:

| File | Purpose |
|---|---|
| `backend/pyproject.toml` | Settings for `pytest` (where tests live, how imports resolve) and `ruff` |
| `backend/requirements.txt` | Runtime dependencies. Comment-only until Phase 4 |
| `backend/requirements-dev.txt` | Development tools: `pytest` and `ruff` |
| `backend/app/__init__.py` | Marks `app` as a Python package (empty) |
| `backend/app/engine/__init__.py` | Marks `engine` as a package (empty) |
| `backend/tests/test_smoke.py` | One small test that imports the engine package, proving the setup works |
| `README.md` | Minimal setup instructions, extended in later phases |

What you will run (Claude will give the exact commands with the files): version checks for Python, Node.js, npm, and Git; create the virtual environment in `backend`; install from `requirements-dev.txt`; run `pytest` and `ruff`; run `pip freeze` and paste everything back. Claude then pins exact versions from your real `pip freeze` output, rather than guessing them.

Done when: you have pasted output showing the smoke test passing and `ruff` reporting no problems.

## Implementation roadmap

Each phase ends with working, tested software before the next begins. Phase 0 is complete. All other phases are **not started**.

| Phase | Goal | Done when |
|---|---|---|
| 0 | Planning and documentation | Docs reviewed and first commit made (review corrections still to be committed) |
| 1 | Toolchain check, backend skeleton, minimal README | You have run the version checks, created the Python virtual environment, and a trivial `pytest` test passes with output shared |
| 2 | Core engine: models, validation, normalization, weighted-sum scoring, ranking | The hand-calculated reference example passes as tests, with output shared |
| 3 | Constraints, ties, explanation data, and "Why not X?" comparison. Normalization scope decided first | Constraint, tie, and explanation tests pass |
| 4 | API: `/api/health` and `/api/analyze` | API tests pass and you can call the endpoint from the browser docs page |
| 5 | Frontend skeleton and first vertical slice: input form, call API, show ranking, contribution chart, and normalized values | You can enter the laptop example in the browser and see B, A, C |
| 6 | Sensitivity: weight sweep, switching points, then seeded rank-stability simulation | Reference switching point of 0.5 is found; charts display |
| 7 | Scenarios (weights only) | Two scenarios can be compared side by side |
| 8 | Templates | At least two templates load and validate |
| 9 | Decision journal with SQLite and outcome reviews | Save, reload, and review work, with tests |
| 10 | Exports: JSON, CSV, printable report | Round-trip import and export reproduces the same result |
| 11 | Optional AI-assisted parsing (feature flag, fake-provider tests) | Disabled path and failure messages work; enabled path tested only if you decide to set up a key |
| 12 | Polish, accessibility, final README, demo script, full manual checklist | Checklist in `docs/TESTING.md` completed with results recorded |

## Decisions log

| Date | Decision | Status |
|---|---|---|
| 2026-10-25 | Documentation first, before any application code | Agreed |
| 2026-10-25 | Keep `filesystem_test.txt` for now | Agreed |
| 2026-10-25 | Proposed stack: Next.js frontend, FastAPI backend, SQLite, local run for the demo | Proposed, awaiting your confirmation |
| 2026-10-25 | Journal storage through built-in `sqlite3` rather than an ORM | Proposed, confirm at Phase 9 |
| 2026-10-25 | Scenarios override weights only in the first version | Proposed |
| 2026-10-25 | Normalization scope (all options or eligible options only) | Open, decide before Phase 3 |

## Session notes

- 2026-10-25: Created the planning documents and configuration files listed above. The first draft dated its entries 2026-10-24; the Git log shows work happening on 2026-10-25 in your timezone, so dates were corrected.
- 2026-10-25: Consistency review. Corrections made:
  - Scenarios now consistently mean weight overrides only.
  - Added non-functional requirements, qualitative-rating guidance, and first-version exclusions (target-value criteria, missing values).
  - Added "Known limitations" (relative scores, rank reversal, outliers, linear trade-offs).
  - Tightened limits: numeric magnitude, weight range, simulation runs, sweep steps, and a note that body size is not enforced by default.
  - Defined edge cases: simulation tie credit, sensitivity when all other weights are zero.
  - Security rules added: localhost-only backend, untrusted imports, CSV formula safety, pinned Python versions.
  - Demo privacy: reset the journal between visitors.
  - Replaced SQLAlchemy with built-in `sqlite3` as the proposal, and changed `DATABASE_URL` to `DATABASE_PATH` to match.
  - `.gitignore` now covers SQLite journal, WAL, and shm files.
  - Recorded normalization scope as an open decision, with both sets of expected numbers in `docs/TESTING.md`.
  - Roadmap: README starts in Phase 1, "Why not X?" assigned to Phase 3.
