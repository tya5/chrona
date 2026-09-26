# Implementation Amendment — Lane Rows After the Phase and Version Correction (#467)

**Amends:** the [L0–L4 plan](issue-467-collision-aware-lane-rows-implementation-plan-2026-09-26.md). **Authority:** [phase and version correction](../../design/issue-467-lane-rows-phase-and-version-correction-2026-09-27.md), [review](../../reviews/current/issue-467-lane-rows-phase-correction-architecture-review-2026-09-27.md).

- **Environment:** the plan's `.venv311` reads as the session's project virtual environment (`.venv`).
- **L0:** unchanged. The measured feasibility of HALCYON `02` (≤12 lanes; `structure → avionics → bus-test` on one lane) is computed with the actual font metrics and the phase-1 required-label footprint (title plus delta, with the stagger ladder), and published as a research record before L1.
- **L1:** "v0.23" reads as the next free View version (expected v0.25, after #426's v0.24). Copy the schema from the live View schema; mark the predecessor `transitioning`; migrate the View `version` lines with `git ls-files`-scoped edits only.
- **L2:**
  - lane names and deltas are placed in phase 1 inside their lane's reserved footprint, before dependencies;
  - the lane row requirement goes through `required_row_block_extents` together with the #480 `text_line_block`;
  - the lane table goes through `measure_table_columns` (#487).
- **L3:** the migration adds `default-draft.yaml` and the five catalogue preset Views (acceptance row 5), alongside `01`, `02` and a non-hierarchy third slide (`03` or `04`). Every changed route and label is attributed.
- **L4:** unchanged.

## Implementation note: the lane table is Layout-synthesized, not pre-normalized

`rows.mode: lanes` forbids `tableColumns` at the schema/contract boundary (#467 L1), so the lane `Lane`/`Items` columns cannot be produced the way an authored table cell is today: upstream `review/v05_content.py` normalization runs before Layout ever packs a lane, and lane membership is a Layout decision (Specification 38 §3.1), not a View or Projection fact. `compose_surface_layout` therefore synthesizes the lane table's columns and cells itself, from the same completed rows the mark/label geometry uses, immediately before feeding them through the unchanged `measure_table_columns`/`place_table_columns` path every other table cell uses (#487). This is a deliberate, reviewed exception to "Layout only measures text a caller supplies": for lanes, Layout is also the source of that text, because only Layout knows the packing. `automatic` and `explicit` table content is unaffected; their columns/cells still come from `review/v05_content.py` exactly as before.
