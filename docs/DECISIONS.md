# Decision Log

Important engineering and product decisions, the alternatives considered, and the reasons. Newest decisions go at the bottom. A decision that changes is marked "Superseded by" instead of being deleted.

## D-001: Keep the existing 12-phase roadmap (2026-10-25)

**Context.** The master specification lists 9 phases. `docs/progress.md` already has a finer-grained 12-phase roadmap with a "written vs verified" rule.
**Decision.** Keep the 12-phase roadmap. It covers the same modules in the same dependency order (foundation, engine, API, frontend slice, sensitivity and scenarios, journal, exports, AI, polish and Science Fest delivery).
**Added to the roadmap by the spec:** a decision-tree builder, soft preferences, and the Science Fest evaluation plan (all in Phase 12 or a later slot; see `docs/progress.md`).
**Consequence.** No renumbering, no confusion between two plans.

## D-002: Normalize over eligible options only (2026-10-25)

**Context.** Open decision 3 in `docs/ARCHITECTURE.md`.
**Options.** (a) Normalize over all entered options. (b) Normalize over options that pass the hard constraints.
**Decision.** (b). An option that is ruled out behaves as if it was never entered, which is easier to explain and avoids a ruled-out option stretching the scale.
**Cost.** Toggling a constraint changes the scores of the remaining options. The product must say so. Documented in `docs/SCORING_MODEL.md`.

## D-003: Scenarios may override weights, option values, and option availability (2026-10-25)

**Context.** `PROJECT_GUIDE.md` said scenarios override weights only. The specification asks for budget decreases, shorter deadlines, increased costs, and unavailable options.
**Decision.** A scenario is a copy of the decision model with named overrides (weights, individual values, constraint thresholds, an option marked unavailable). The engine stays stateless: it analyzes whatever model it is given, so no engine change is needed. The original is never modified.
**Consequence.** The guide and architecture documents were updated. Scenario work happens in the roadmap's Phase 7.

## D-004: Constant criterion normalizes to 0.5 (2026-10-25)

**Decision.** If every eligible option has the same value on a criterion, each gets 0.5 for it. Neutral, keeps contributions summing to the score, and avoids dividing by zero. Tested.

## D-005: Missing values are rejected (2026-10-25)

**Decision.** Every option needs a value on every criterion. Treating a blank as zero would silently reward or punish an option. The interface should help users fill gaps or remove a criterion instead. Revisit only with an explicit, user-visible rule.

## D-006: Engine uses only the Python standard library (2026-10-25)

**Context.** The engine must not import web, database, or AI code (`PROJECT_GUIDE.md`, section 6).
**Decision.** The engine uses plain frozen dataclasses and its own validation, and raises `ModelValidationError` with a list of problems. Pydantic validates requests at the API layer (Phase 4) and converts them into engine models.
**Benefit.** Engine tests need only `pytest`, so the pending Phase 1 install is enough to run them. No new dependency.

## D-007: Hard constraints in the engine; soft preferences later (2026-10-25)

**Decision.** Hard constraints are implemented now. Soft preferences (nice-to-have limits that influence but do not exclude) are deferred to the constraints work in the roadmap. They will be shown separately and will never remove an option. A soft preference must not be presented as a hard rule.

## D-008: AI layer is provider-independent (2026-10-25)

**Context.** `.env.example` named a single provider key.
**Decision.** When Phase 11 starts, the parser sits behind a small interface with a fake provider for tests. A real provider is chosen only after checking current official documentation and pricing. The core product never depends on it. The current `.env.example` placeholders stay until then.

## D-009: Tailwind CSS for the frontend (2026-10-25)

**Decision.** Use Tailwind CSS (offered by the Next.js setup) with Recharts for charts. Confirm at frontend scaffolding in Phase 5. Hand-written types, same-origin rewrite versus CORS to be decided in Phase 5.

## D-010: One handoff file (2026-10-25)

**Decision.** `HANDOFF.md` at the project root is the single authoritative handoff. `docs/progress.md` holds the status table and roadmap; `HANDOFF.md` holds the short "state and exact next step" note.
