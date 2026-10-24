# What If? Decision Intelligence Platform

An explainable tool for comparing options against weighted criteria and hard limits, then showing how stable the result is. It is a decision-analysis tool, not a chatbot.

**Status:** early development. The decision engine (scoring, constraints, explanations), a FastAPI backend with templates, and 83 automated tests pass (see `docs/TESTING.md`). There is no database or user interface yet. See `HANDOFF.md` for the current state and next step, and `PROJECT_GUIDE.md` for the full plan.

> The setup steps worked on the project owner's Windows machine on 2026-10-25. The virtual-environment step can take a few minutes with no output; do not interrupt it. If a step fails, copy the full error text.

## Quick start (Windows)

The one-step way, from the project folder:

```powershell
.\scripts\setup-backend.cmd
```

It creates the virtual environment, installs dependencies, runs the tests and the code checker, and prints the installed versions. Creating the environment can look frozen for a few minutes; do not close the window. Then start the backend with `.\scripts\run-backend.cmd` and open http://127.0.0.1:8000/docs to try the API. The step-by-step version of the same process follows below.

## What you need

- Windows with the VS Code terminal (PowerShell is the default shell)
- Python 3.13 (the project owner reports 3.13.14)
- Git

Node.js and npm are not needed until the frontend is built in Phase 5.

## Backend setup (Windows, PowerShell)

Run these commands in the VS Code terminal (Terminal menu, New Terminal). Run them one at a time and read the output before moving on.

### 1. Go to the backend folder

The terminal usually opens in the project folder, so this is enough:

```powershell
cd backend
```

If you are somewhere else, use the full path in quotes (the quotes are needed because the path contains spaces):

```powershell
cd "E:\apps and codes j\WhatIf2.0\backend"
```

### 2. Check your tools

```powershell
python --version
git --version
```

`python --version` should print a Python 3.13 version. If it opens the Microsoft Store or says the command is not found, try `py --version`. If that works, use `py` instead of `python` for the next step only.

### 3. Create a virtual environment

A virtual environment is a private folder of Python packages for this project, so nothing is installed system-wide. It is created once:

```powershell
python -m venv .venv
```

The `.venv` folder is ignored by Git. Never commit it.

### 4. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

The prompt should now start with `(.venv)`. Activate again each time you open a new terminal.

If PowerShell says that running scripts is disabled, do not change system settings. Skip activation and put `.\.venv\Scripts\python.exe` in front of every command below instead of `python`. For example:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### 5. Install the development tools

```powershell
python -m pip install -r requirements-dev.txt
```

This installs `pytest` (runs tests) and `ruff` (checks code style and common mistakes). A notice about a newer version of pip is harmless.

### 6. Run the tests

```powershell
python -m pytest
```

The project has two smoke tests plus the engine tests in `tests/engine/`. All of them should pass. If any fail, copy the full output.

### 7. Run the code checker

```powershell
python -m ruff check .
```

It should report that all checks passed.

### 8. List installed versions

```powershell
python -m pip freeze
```

This prints every installed package and its exact version. It is used to pin exact versions in the requirements files so that installs are reproducible.

## Common problems

| What you see | Likely cause and fix |
|---|---|
| `python` is not recognized, or opens the Microsoft Store | Use `py` instead, or reinstall Python and tick "Add Python to PATH" |
| "running scripts is disabled on this system" | Use the `.\.venv\Scripts\python.exe` form shown in step 4 |
| `No module named pytest` or `No module named ruff` | The virtual environment is not active, or step 5 was not run |
| `No module named 'app'` | You are not in the `backend` folder. Run `cd backend` first |
| Odd path errors | The project path has spaces. Quote it, or consider moving the project to a path without spaces |

## Project layout (so far)

```
PROJECT_GUIDE.md      product vision, principles, standards, security rules
docs/                 architecture, testing plan, progress
backend/
  app/                backend code (engine, API, templates)
    engine/           decision-analysis logic (written, awaiting its first test run)
  tests/              automated tests
  pyproject.toml      pytest and ruff settings
  requirements.txt    runtime dependencies (fastapi, uvicorn)
  requirements-dev.txt  development tools
```

## Further reading

- `PROJECT_GUIDE.md` for the plan, rules, and workflow
- `docs/ARCHITECTURE.md` for the proposed design
- `docs/TESTING.md` for the testing plan
- `docs/progress.md` for what is done and what comes next
