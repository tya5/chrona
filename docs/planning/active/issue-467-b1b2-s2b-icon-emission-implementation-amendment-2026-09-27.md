# Implementation Amendment — S2b icon emission closure (#467, #494)

**Public design base:** `3b42667b3aaf19d1962d1eda2deccd1d2f8d88f1`. **Amends:** [S2 implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md) and [rule-based L3 plan](issue-467-494-rule-based-lane-acceptance-implementation-plan-2026-09-27.md). **Design/review:** [icon emission correction](../../design/issue-467-b1b2-s2b-icon-emission-closure-correction-2026-09-27.md), [whole-architecture review](../../reviews/current/issue-467-b1b2-s2b-icon-emission-architecture-review-2026-09-27.md), Specs [38](../../specification/38-review-row-composition.md) and [46](../../specification/46-completed-scene-paint.md).

This plan covers mark-target icons and the reusable typed emission payload. Packed-label `labelVisual` icons have a separate [design plan](issue-467-b1b2-lane-label-visual-design-plan-2026-09-27.md); S2b publication cannot treat them as complete until that selected design and implementation amendment are published and implemented. The S2a icon type unit below may proceed independently, but no old automatic label-icon coordinates may be copied into lanes.

| Publishable unit | Owners and migration | Focused verification and gate |
| --- | --- | --- |
| **S2a icon type/validator** | `src/chrona/presentation/layout/lane_allocation.py` typed `LaneIconProjection` on source-keyed facets; allocation unit tests and diagnostic inventory. No public schema/resource/output change. | Vector two-path common metadata, exact indices 0..n−1, distinct completed path paint/cap/join/scaled widths, mismatch/missing index rejection, raster one-facet exact bytes/viewport, repeated projection identity. Footprints remain per path and placed viewport is not an extra footprint. Focused tests, diagnostic/reachability check, one 28-slide materializer batch with unchanged bytes. Publish/review independently while lane guard closed. |
| **S2b mapper/preflight completion** | Layout projection mapper/test helpers only. Copy completed `IconPlacement` common metadata and each `IconPathPlacement` into per-path facets; raster copies exact payload. Preserve published port-host bounds and explicit `as_of`. | Mapper→allocator→preflight fixtures for vector/raster/icons plus planned/comparison/Actual/progress/attached point; no icon payload reload or second transform/stroke scale. Focused tests, one public-materializer check, unchanged automatic bytes. Publish/review independently; do not activate lane mode. |
| **B2 icon projection seam** | Layout composer plan transport and Scene builder path grouping, after the one-plan seam. No adapter-specific geometry policy. | Validate emission-group common fields and contiguous path indices from the immutable plan, emit exactly one Scene ICON per `placement_id` with completed paths in order, exact asset/alternative/decorative/capability/slot/paint-order/raster facts. Direct hidden lane Scene test plus output byte comparison. Any mismatch returns to design before public activation. |

The S2b icon mapper remains paused until the S2a type slice is published. It may proceed alongside independent Scene lane-anchor carrier work after that gate. Keep focused local suites and batch public materializers/SVG diff per material unit; CI supplies full matrix at release. Fetch `origin/main`, inspect staged/generated diffs and exact ahead/behind before each serial push; verify remote commit and CI/PR state. No numerical lane-count target or forced third label row is reintroduced.

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
