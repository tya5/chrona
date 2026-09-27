# Slice Review — View v0.26: I479-1, I479-3 and A486-2 (#479, #486)

**Designs:**
- #479: [design](../../design/issue-479-project-generic-presets-design-2026-09-27.md), including amendments 1 and 2.
- #486: [design](../../design/issue-486-attached-milestones-design-2026-09-27.md).

**CI:** pending.

## Version decision

The plans reserved v0.25 for #466, v0.26 for #467 and v0.27 for #479. #466 took v0.25. #467's lane work is not landable: it is pushed as `wip/issue-467-lane-rows`, and the reasons are on the issue. So this slice takes **v0.26**, and #467 takes the next free version when it lands. v0.25 moves to `transitioning`, and every View in the repository moves to v0.26.

## Contents

- **I479-1 (View and Projection):**
  - `grouping.order: {by: earliestPlannedStart}`;
  - no group header when every selected item lacks the grouping field;
  - `colorEncoding.domain: firstAppearance`, with the Theme `colorScales.<id>.palette` (Theme v0.11, extended in place). An item without the field keeps its role's own paint.
  - `labels.placement: both`, with `E_VIEW_LABELS_BOTH_TABLE_TITLE`.
- **I479-3 (catalogue):** the five catalogue presets move to data-derived group order and to `both`. The three owner-scale Themes use a `firstAppearance` palette over the new generic `series-1…6` Scheme slots. Per-group `group:<value>.fill` bindings are removed. The bundle legends (`detail.yaml`) become preset-library `detailProfile` members, and so do the Editorial and Technical print legends. `elevated-light` prefers `v0.7-svg`. Amendment 1 records the three decisions this needed.
- **A486-2 (rows):** `rows.points: attached` is the new default. A point that `attachesTo` a selected span moves onto that span's row, and its required plot label reads "title · date · delta". `own-row` restores a row per point. `predecessor` attaches first and infers only for the remaining points.

## Evidence

- **Scenes:** all 28 public Scenes change only in provenance: the View content identity (its version line) and, for HALCYON-1, the Scheme identity (the additive `series-*` slots). `classify.py` reports no structural change.
- **SVGs:** no public SVG changes. No committed slide uses the new vocabulary, and no committed project carries `attachesTo`.
- **Tests:**
  - [`test_project_generic_view.py`](../../../tests/integration/test_project_generic_view.py): group order, the lone header, first appearance (including an item without the field), and `both` with its validator.
  - [`test_project_generic_presets.py`](../../../tests/integration/test_project_generic_presets.py): every catalogue preset against HALCYON-1 and the `chrona init` starter, a bundle scan for example-project values, legends, and `elevated-light`'s gradient without a flag.
  - [`test_attached_milestones.py`](../../../tests/integration/test_attached_milestones.py): host-row placement, the label text, and the `own-row` restore.
- **Checks:** full `pytest` 1414 passed and 25 skipped; conformance PASS.

## Not in this slice

- #479 I479-4, the literal acceptance review.
- #486 A486-3 (pinning attached points in lanes, which needs #467).
- #486 A486-4 (committed example and acceptance).
