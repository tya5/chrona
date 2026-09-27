# Implementation Amendment — Atomic lane label visuals (#467, #494)

**Public design base:** `6c7826e4173e6ce058ba8ff2d00eff60222b8bed`. **Amends:** [S2 mapper implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md), [icon emission plan](issue-467-b1b2-s2b-icon-emission-implementation-amendment-2026-09-27.md), and [rule-based L3 plan](issue-467-494-rule-based-lane-acceptance-implementation-plan-2026-09-27.md). **Design/review:** [atomic label-visual correction](../../design/issue-467-b1b2-lane-label-visual-correction-2026-09-27.md), [whole-architecture review](../../reviews/current/issue-467-b1b2-lane-label-visual-architecture-review-2026-09-27.md), Specs [38](../../specification/38-review-row-composition.md), [46](../../specification/46-completed-scene-paint.md), [50](../../specification/50-constraint-driven-gantt-surface-quality.md).

| Publishable unit | Owners/files | Focused evidence and boundary |
| --- | --- | --- |
| **V1 shared measured visual advances** | Refactor only the reusable Layout `resolve_label_visual_advances`/text-visual measurement helper in `surface_composer.py` or a focused Layout helper; new unit fixtures. Preserve existing automatic/explicit call path and diagnostics. | Exact leading/trailing/both advances, typography ratio/gap, canonical visual target and duplicate side, title+delta measured text, missing asset/metric faults. Focused tests and batch 28-slide materializer/Scene/SVG byte check. Publish/review before lane candidate use. |
| **V2 finite lane-label variants and allocator** | Typed `LaneRequiredLabel`/`LaneLabelVariant`/selected placement in `layout/lane_allocation.py` or a focused adjacent Layout module; S2b mapper/preflight transport and unit fixtures. Each rung carries completed component text/icon geometry, measured bounds, visible footprints and natural block extent. Neutral allocator only tests/selects; it never loads Theme/catalog. | Mark/label/icon collision symmetry, component exactness, deterministic rung order, no text-only acceptance, new-lane/visible-overflow closure, attached and repeated-source identity, raster/vector path footprint with stroke once. Focused allocator/preflight tests, diagnostic inventory/reachability, unchanged automatic bytes. Publish/review with public lane guard closed. |
| **V3 B2 one-plan emission** | `surface_composer.py`, typed Layout result, `scene/v05_builder.py`, existing Scene v0.6 lane provenance; integration fixtures. Translate selected lane-local bundle once into final coordinates; emit completed text and one ICON per label visual with same lane row/member provenance. Do not call generic post-hoc resolver on those pre-reserved labels. | Direct hidden 02 plus neutral labelled-icon fixture: exact reserved/emitted text+icon bounds, title/delta visibility, phase-one obstacle and #494 no-crossing behavior, Scene no-redundant-lane checker includes icons, old automatic bytes unchanged. Batch generated Scene/SVG/PNG diff and inspect rendered labels/icons. Publish/review before L3c default/preset activation. |

The new `E_LAYOUT_LANE_LABEL_VISUAL_UNAVAILABLE` reports pre-reserved/emitted mismatch with a source/member path. Existing `E_LAYOUT_VISUAL_TARGET`, `E_LAYOUT_VISUAL_DUPLICATE`, icon/Theme/font diagnostics remain authoritative for their original faults. No View schema syntax or Scene coordinate repair is added. Non-icon S2b work may proceed locally while V1/V2 are built, but S2b cannot be accepted as a complete mapper until the label-icon contract is satisfied. No numeric lane count or forced third row is a gate. Run focused tests per unit; batch public materializers/SVG comparisons and use CI for planned full matrix. Before each serial push fetch `origin/main`, inspect exact commits/staged/generated diff, stop on unexpected remote update, then verify remote commit and relevant CI.

## Literal acceptance retained

### #467

1. A lane row mode exists. On `02-programme-board` the chain `structure → avionics → bus-test` is on one lane, and the lane count is **justified by the rule, not by a target number**. Both checks read the Scene footprints (marks, comparison marks, names, deltas, icons):
   - **No redundant lane.** For every pair of lanes in the same group, moving all items of one into the other would make two footprints collide. The only exception is a pair kept apart by the chain rule, and those pairs are listed.
   - **Lower bound reported.** For each group, report the maximum number of footprints that overlap at one date, next to its lane count, and attribute any difference. The lower bound is reported and explained; it is not a target.
   *(Amended 2026-09-27 twice: "at most 12" and then "at most 14" were arbitrary numbers and are withdrawn; see the comments.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.
