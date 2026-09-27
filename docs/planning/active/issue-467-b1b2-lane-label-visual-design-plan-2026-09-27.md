# Design Plan Amendment — Lane label-visual icons (#467, #494)

**Public base:** `3b42667b3aaf19d1962d1eda2deccd1d2f8d88f1`. **Related:** [S2b icon emission plan](issue-467-b1b2-s2b-icon-projection-design-plan-2026-09-27.md), [rule-based acceptance plan](issue-467-494-rule-based-lane-acceptance-design-plan-2026-09-27.md), and existing Layout `resolve_text_visual_requests`. An S2b preflight audit found two distinct icon owners: `iconMark` belongs to a mark and can use its completed mark placement; `labelVisual` belongs to required text and must move with the selected lane-label rung. Copying automatic-mode label-icon coordinates would break lane geometry. Putting label icons in mark facets would mix label and mark collision ownership.

## Questions, slices and evidence

Define a typed measured label bundle for each packed root/attached member: required title/delta text plus zero or more resolved leading/trailing visual icons, their source/asset identity, measured widths/gaps/heights, and exact placement intent. Decide whether the existing generic text-visual measurement helper can be extracted for both automatic and lanes without output changes. Layout must evaluate the whole bundle at each finite label rung with exact text/icon visible footprints, reserve its natural row height, and retain the selected completed text/icon geometry in the immutable lane plan. Scene projects the completed values; adapters serialize. View continues to select visual side/ref, Theme controls size ratios, and asset closure supplies normalized vector/raster facts; no Scene/adapter coordinate repair or old automatic-coordinate copy.

Review this against Spec 38 lane allocation, Spec 46 paint/geometry, Spec 50 phase-one required text obstacles, #466 route/no-crossing policy, S2 source-keyed mark facets, #350 icon catalog, current text-visual diagnostics and #498 packaged defaults. Determine exact behavior for a missing asset, duplicate sides, label-visible-overflow, delta ordering, icon+text baseline, multi-line text, and whether a non-label visual target is unaffected. Publish this design plan, then the selected design/spec/whole-architecture review, then an implementation-plan amendment before code. Independent non-icon S2b mapping may continue locally; label-visual/icon slices and B2 activation wait for this contract.

Focused evidence: neutral required label with leading/trailing raster/vector icons across stagger/inline rungs; exact icon path/stroke and text bounds, collision and route-obstacle identity, no lost name/delta, attached point and repeated source; generated Scene/SVG inspection for a lane fixture; automatic byte characterization and one batched public materializer check. If a label icon cannot fit, use declared visible-overflow or a new lane per approved lane policy, never suppress the packed name.

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
