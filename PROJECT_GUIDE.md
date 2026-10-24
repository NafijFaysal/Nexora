# What If? Decision Intelligence Platform: Project Guide

This is the reference document for the project. Read it before starting any work session, and update it when a decision changes. Related documents:

- `docs/ARCHITECTURE.md`: how the system is structured
- `docs/TESTING.md`: what is tested and how to verify it
- `docs/progress.md`: what is done, what is next

## 1. Product vision

What If? helps a person make a hard choice by structuring it, scoring it transparently, and showing how fragile or robust the result is.

The user describes a decision (the options, what matters, how much each thing matters, and any non-negotiable limits). The platform ranks the options and then explains the ranking: which criteria drove it, what would have to change for a different option to win, and how confident the result really is.

It is a **decision-analysis tool**, not a chatbot. All scoring, ranking, and sensitivity numbers come from deterministic, testable code. AI, if enabled, only helps with turning free text into structured input, and always under the user's review.

### What the platform should help a user answer

- Which option best fits what I care about, and why?
- Which options are ruled out by my hard limits?
- If my priorities shift a little, does the answer change?
- At what point does a different option win?
- What did I decide before, and how did it turn out?

### Honest framing

- The methods used (weighted-sum scoring, constraint filtering, one-at-a-time sensitivity, weight-sampling simulation) are standard, well-documented techniques. We make no claim that the mathematics is new. The goal is a clear, trustworthy explanation of results, not novel methods.
- Intended users below are working assumptions. No user research has been done, and none should be claimed.
- A score is only as good as the inputs. The product should say so plainly rather than imply false precision.

## 2. Intended users (working assumptions, not validated)

- Students and families comparing choices such as courses, schools, or laptops.
- Early-career people weighing job offers or places to live.
- Small groups or clubs choosing between vendors, tools, or plans.
- Science Fest visitors trying a short, guided example.

Design for someone who is not technical and has about five minutes.

## 3. Principles

1. **Explainable first.** Every result must be traceable to inputs the user entered. No black boxes in the scoring path.
2. **Deterministic core.** The same input always gives the same output. Randomized features (simulation) use a fixed, recorded seed so results can be reproduced.
3. **Honest uncertainty.** Show sensitivity and ties. Never present a narrow win as a clear one.
4. **Works without AI.** AI is an optional convenience. The product must be fully usable with it switched off.
5. **User stays in control.** AI-parsed input is shown for review and edit before it is used.
6. **Private by default.** Decisions can be personal. Nothing leaves the user's machine unless they turn on a feature that sends it.
7. **Low cost to run.** No paid service is required to run, test, or demo the core product.
8. **Tested, not just demonstrated.** A feature is not done until it has automated tests and a manual check recorded in `docs/TESTING.md` (verification record) and `docs/progress.md` (status).
9. **Small steps.** Build thin vertical slices that work end to end, then widen them.

## 4. Planned features

Each item is a plan, not a promise. Status is tracked in `docs/progress.md`.

### Core analysis

- **Decision model:** options, criteria, weights, and numeric values for each option on each criterion.
- **Criterion direction:** each criterion is either "higher is better" (benefit) or "lower is better" (cost).
- **Scoring:** weighted-sum model with min-max normalization (first method). Further methods (for example TOPSIS) may be added later behind a clear explanation of how they differ.
- **Constraints:** hard limits that mark an option as not allowed (for example "price must be at most 900"), with the reason shown for each excluded option.
- **Ranking:** ordered results with explicit tie handling.

### Explainability and visualization

- Per-criterion contribution breakdown for each option (stacked bars).
- Plain-language explanation generated deterministically from the numbers (templated text, not AI).
- "Why not X?" comparison between any two options.
- Weight display that makes the normalization visible.

### Scenario and sensitivity analysis

- **Scenarios:** named sets of weights or values (for example "budget-focused" and "quality-focused") compared side by side.
- **One-at-a-time sensitivity:** sweep one weight while rescaling the others, and chart the scores.
- **Switching points:** the weight value at which the top-ranked option changes.
- **Rank stability:** repeatedly sample plausible weights (seeded) and report how often each option ranks first.

### Decision journal

- Save a decision with its inputs, result, and the user's reasoning.
- Record the option actually chosen, and later add an outcome review (what happened, was the decision good in hindsight).
- Browse and search past decisions.

### Templates

- Prebuilt starting points stored as JSON (for example laptop purchase, job offer, study option).
- Templates provide criteria and suggested weights only; the user supplies the values.

### Optional AI-assisted input parsing

- The user pastes free text such as "I'm choosing between three laptops, I care most about battery and price".
- The AI proposes structured options, criteria, and weights. The user reviews and edits before analysis.
- Disabled by default. Feature-flagged. Never required.

### Exports

- JSON export and import of a full decision model (also useful for sharing and for tests).
- CSV export of scores and rankings.
- A printable report page (the browser's "Save as PDF" covers PDF output, so no PDF library is needed at first).

### Out of scope for now

User accounts, multi-user collaboration, mobile apps, payments, and public hosting of personal data. See open decisions in `docs/ARCHITECTURE.md`.

## 5. Architecture direction (summary)

Details are in `docs/ARCHITECTURE.md`. In short:

- **Frontend:** Next.js with TypeScript in `frontend/`.
- **Backend:** FastAPI (Python) in `backend/`.
- **Analysis engine:** a plain Python package with no web or database code, tested on its own.
- **Storage:** SQLite file for the journal.
- **AI:** optional module behind a feature flag, with all output validated.
- **Run model:** both parts run locally on one laptop. This is the most reliable setup for a live demo.

## 6. Coding standards

### General

- Prefer clear, boring code over clever code. A beginner should be able to read it.
- Keep functions small and single-purpose. Use descriptive names.
- Comments explain *why* when a decision is non-obvious (for example why min-max normalization is used, or why ties are broken a certain way). Do not comment what the code plainly says.
- No dead code and no commented-out code in commits.
- Do not add a dependency without a written reason in `docs/ARCHITECTURE.md`. Fewer dependencies means fewer things to break and fewer things to learn.

### Python (backend)

- Type hints on all function signatures.
- Pydantic models define and validate all external input.
- The `engine` package must not import FastAPI, the database, or the AI module.
- Use `ruff` for linting and formatting and `pytest` for tests (to be set up in Phase 1).
- Floating-point comparisons in tests use a tolerance, never exact equality.

### TypeScript (frontend)

- TypeScript strict mode on.
- Keep calculation logic out of the frontend. The frontend collects input and displays results; the backend computes them.
- One component per file, small components, no `any` without a comment explaining why.
- Use ESLint (provided by the Next.js setup).
- Charts and tables need text alternatives or labels so they are usable with a keyboard and screen reader.

### Git

- Small commits with a short, imperative message (for example `Add weighted-sum scoring`).
- Work on `main` while learning; use short-lived feature branches once the basics are comfortable.
- Never commit `.env` files, database files, `node_modules`, or `.venv`.

## 7. Security and privacy rules

1. **No secrets in Git.** API keys live only in untracked `.env` files. `.env.example` holds placeholders only. If a real key is ever committed, treat it as leaked: revoke it, then replace it.
2. **Validate on the server.** The frontend's checks are for convenience only. The backend validates every request with Pydantic, including types, ranges, and sizes.
3. **Limit sizes.** Cap the number of options, criteria, text lengths, and request body size, to prevent accidental or deliberate overload. Specific limits are set in code and documented in `docs/ARCHITECTURE.md`.
4. **No dynamic code execution.** Never use `eval`, `exec`, or user-supplied formulas.
5. **Parameterized database access.** Use the ORM or query parameters. Never build SQL by joining strings.
6. **Safe rendering.** Rely on React's default escaping. Do not use `dangerouslySetInnerHTML` with user or AI text.
7. **Narrow CORS.** Allow only the known frontend origin.
8. **AI output is untrusted.** Validate AI responses against the same schema as manual input. Show them to the user for review. Never act on instructions embedded in pasted text, and never let AI output reach a file path, command, or query.
9. **AI is opt-in and bounded.** Off by default, input length capped, and sent only when the user triggers it. Warn the user that pasted text is sent to an external service.
10. **Minimal logging.** Do not log decision content, pasted text, or API keys.
11. **Keep dependencies tidy.** Commit lock files, install from them, and review `npm audit` and `pip` advisories periodically.
12. **No public deployment of personal data without a plan.** Without accounts, a shared public database would mix users' decisions. Do not deploy publicly until storage and access are decided.

## 8. Development workflow

Claude can read and write project files but **cannot run anything on your computer**. The working loop is therefore:

1. Claude proposes a small step and writes or edits the files.
2. You run the stated commands in the VS Code terminal.
3. You paste back the full output, including errors.
4. Claude reads the real output and fixes or moves on.

Rules that follow from this:

- Nothing counts as working until you have run it and shared the result.
- `docs/progress.md` separates **written** (files exist) from **verified** (you ran it and confirmed). Only verified work is called done.
- Claude does not state or imply that tests passed, packages installed, or the app started unless you provided that output.

### Per-feature checklist

1. Define the behavior in plain language, with a hand-calculated example where numbers are involved.
2. Write the tests first or alongside the code.
3. Implement.
4. Run automated tests (you run them, Claude reads the output).
5. Do the manual check listed in `docs/TESTING.md`.
6. Update `docs/progress.md` and, if a decision changed, the relevant document.
7. Commit.

### Windows notes

- The project path contains spaces (`E:\apps and codes j\WhatIf2.0`). Quote the path in terminal commands. Some tools handle spaces poorly. If an odd path-related error appears, moving the project to a path without spaces (for example `E:\projects\WhatIf2.0`) is a reasonable fix.
- Use the VS Code integrated terminal and note which shell it is (PowerShell is the default). Commands for activating the Python virtual environment differ between shells, and Claude will give the exact form when needed.

## 9. Definition of done

A feature is done when:

- Its behavior is described and its edge cases are listed.
- Automated tests exist and you have run them with the results shared.
- The manual check in `docs/TESTING.md` was performed.
- Documentation is updated.
- It is committed.
