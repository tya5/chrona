# Implementation Amendment 2 — Candidate Placement on Current `main` (#466)

**Amends:** the [C2–C4 plan](issue-466-candidate-placement-implementation-plan-2026-09-26.md). **Authority:** [rebase correction](../../design/issue-466-candidate-placement-rebase-correction-2026-09-27.md).

- **C2:**
  - `schemas/view-v0.23.schema.yaml` reads as "the next free View version": copy it from the live schema, mark the predecessor `transitioning`, and migrate the `version` lines with `git ls-files`-scoped edits. Keep the rung spelling valid alongside `candidates`.
  - `schemas/theme-v0.12.schema.yaml` reads as **additive optional fields in `schemas/theme-v0.11.schema.yaml`**.
  - The byte gate holds: every public slide is unchanged after C2 except the version-line migration's provenance.
- **C3:** unchanged, with HALCYON `02-programme-board` adopting candidates. Note that `02` now uses the wallboard Theme with an as-of chip (#428), group bands including their headers (#481) and a CSS-grid table (#487). Its evidence is regenerated on the 22-slide corpus.
- **C4:** unchanged.
- **Environment:** the project `.venv`. After regenerating evidence, refresh the derived reports and then run conformance.
