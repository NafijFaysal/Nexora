# Changelog

All notable changes. "Written" means the files exist; nothing here counts as verified until `docs/TESTING.md` section 7 records a real test run.

## Unreleased

### Added (83 automated tests pass and ruff is clean; see docs/TESTING.md)
- Decision engine in `backend/app/engine/`: models, validation, min-max normalization, hard constraints, weighted-sum scoring with ties, templated explanations.
- Hand-calculated engine tests in `backend/tests/engine/`.
- `docs/SCORING_MODEL.md`, `docs/DECISIONS.md`, `HANDOFF.md`.
- FastAPI backend: health, analyze, and template endpoints; CORS limits; request size limit; API tests.
- Three illustrative decision templates.
- `scripts/setup-backend.cmd` and `scripts/run-backend.cmd`.

### Changed
- Documentation reconciled with the master specification (scenario scope, decision-tree builder, soft preferences, provider-independent AI, normalization scope decided).

## Earlier (see Git log)
- Project foundation and documentation; documentation consistency review.
