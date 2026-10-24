# Handoff

The single authoritative "where are we" note. Updated: 2026-10-25. Read this first, then `docs/progress.md`.

## State

The backend is **built and verified by automated tests**: `python -m pytest` gave **83 passed** and `python -m ruff check .` gave **All checks passed** (run by you, recorded in `docs/TESTING.md` section 7). That covers the decision engine, the FastAPI API (`/api/health`, `/api/analyze`, `/api/templates`), three templates, and the smoke tests. The frontend has not been started. Nothing has been committed since the second commit.

## Implemented

- Engine (`backend/app/engine/`): validation, min-max normalization over eligible options, hard constraints with reasons, weighted-sum scoring, stable ties, templated explanations. Math in `docs/SCORING_MODEL.md`.
- API (`backend/app/`): analyze and template endpoints, CORS limited to configured origins, 256 KB declared-size limit, `422` with a `problems` list for invalid models.
- Dependencies pinned: fastapi 0.162.0, uvicorn 0.54.0, pytest 9.1.1, ruff 0.17.2, httpx 0.28.1.
- Scripts: `scripts\setup-backend.cmd`, `scripts\run-backend.cmd`.

## Not verified yet

- Running the server and trying `/docs` in a browser (`scripts\run-backend.cmd`, then http://127.0.0.1:8000/docs).
- Everything in the frontend (not started).

## Known items

- Pytest warning: Starlette says `httpx` with its TestClient is deprecated and suggests `httpx2`. Harmless now; revisit later.
- `filesystem_test.txt` can be removed with `git rm` when you decide.
- Not started: frontend, sensitivity analysis, scenarios, journal and SQLite, exports, AI parsing, decision tree builder, soft preferences, Science Fest evaluation plan.

## Commands for you now

**1. Commit the verified work** (PowerShell, from the project folder):

```powershell
cd "E:\apps and codes j\WhatIf2.0"
git status --short
git add -A
git commit -m "Add decision engine, API, templates, and tests"
git log --oneline -n 3
```

`git status --short` should not list `.venv`, `.pytest_cache`, or `.ruff_cache` (they are ignored). If it does, stop and paste the output.

**2. Scaffold the frontend** (answer any extra prompts with the defaults):

```powershell
npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --use-npm --import-alias "@/*"
```

Paste the output, and then `dir frontend\src\app`. Claude will write the interface on top of whatever this generates.

## Next (Claude)

Phase 5: a Next.js page with an input form (options, criteria, weights, values, constraints, templates), a call to `/api/analyze` through a same-origin rewrite, a ranking table, contribution bars, constraint reasons, and the explanation text. Then sensitivity analysis and scenarios.

## Decisions still open

See `docs/DECISIONS.md` and `docs/ARCHITECTURE.md` section 11: public hosting and storage, AI provider and who pays, tie tolerance defaults, repository visibility and license.
