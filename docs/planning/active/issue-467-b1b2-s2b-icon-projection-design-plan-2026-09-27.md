# Design Plan Amendment — S2b completed icon projection closure (#467, #494)

**Public base:** `ef5d5ebf3db86ff02b0a324fa8161936d7d4e57b`. **Amends:** [S2 facet/count/as-of design plan](issue-467-b1b2-facet-count-asof-design-plan-2026-09-27.md) and [S2b implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). The S2b mapper has paused its icon slice before publication: the source-keyed facet type retains completed path coordinates and collision footprints but not enough typed icon asset, path style/order or resource metadata to project the existing one-primitive Scene icon without rebuilding from the icon payload. Non-icon mapping may continue locally; no incomplete S2b slice is publishable.

## Design questions and boundaries

Choose a typed, immutable Layout closure that keeps vector icon **per-path collision facets** and the existing **one Scene ICON primitive per IconPlacement** connected by explicit emission-group identity and path order. Preserve normalized asset identity, selected icon ID, viewport, already-scaled per-path paint/stroke/cap/join, raster bytes where applicable, alternative/decorative/accessibility facts, visual-capability source, slot and paint order. Determine which facts belong on each path facet versus one owning facet, and validate grouping without duplicating or remeasuring geometry. B2 must copy the closure to Scene; it must not reload assets, rebuild normalized paths, infer IDs, or resolve adapter-specific paint. Review against S1 Layout geometry ownership, S2 source-keyed facet design, Spec 38/46, Scene v0.6 and its paint resolver, Theme/icon catalog contracts, #466 obstacle phase and #494 route requirements.

Publish this plan before choosing code. Then publish a design correction, normative Spec 38/46 adjustment if needed, whole-architecture review, and an implementation-plan amendment. Only then resume the icon mapper and focused tests. Evidence must cover multi-path vector order and paint, scaled stroke exactly once, clipped/raster viewport, repeated source instances, missing/mismatched asset metadata, one Scene icon per emission group, and unchanged automatic public bytes. The public lane guard stays closed. This gap does not change the owner-amended rule-based #467 acceptance or force a lane count.

## Literal issue acceptance retained

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
