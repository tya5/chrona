# Design Plan Amendment — S2b semantic-port host bounds (#467, #494)

**Public base:** `9dbd6d503b9763416003a19c4921e1519cfa345d`. **Amends:** [S2 facet design plan](issue-467-b1b2-facet-count-asof-design-plan-2026-09-27.md) and its [implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md). S2b is paused before a product commit because the published facet invariant requires every semantic relation port inside one emitted primitive's unexpanded bounds, while Layout's completed `MarkPlacement` ports belong to the mark-level host slot. A valid contain-center glyph can have visible part bounds strictly inside that slot, leaving its start/end ports outside every emitted part.

## Use case, decision, evidence

The direct projection mapper must preserve completed planned/point glyph paths, exact visible footprint and relation/annotation ports without inventing extra primitives or widening primitive geometry. Decide whether ports remain source-keyed on one facet with explicit semantic host bounds, or move to a mark-level carrier; reject a loose port-without-host invariant. Check the selected #466 anchor/port design, the #467 facet contract, Spec 38/50, Scene projection, icon/point/attached variants, and repeated projection instances. The selected contract must state identity, containment, missing-host diagnostic, and whether View/Scene/public schemas change. Review whole-architecture consistency before code.

Focused evidence: construct a legal contain-center glyph in a wider mark slot, assert start/end ports outside the primitive bounds but inside the completed semantic host; preserve exact primitive/visible footprint and source identities. Include a point/attached variant and reject ports outside the host. Run mapper→allocator→preflight tests and one batched public-materializer check; automatic bytes must remain unchanged. Publish this design plan, then design/spec/review, then implementation-plan amendment, then resume S2b code and verification. B2 remains downstream of accepted S2b; the separate fourteen-lane owner amendment is unaffected.

## Literal issue criteria and dependency

All six #467 and three #494 literal acceptance rows remain deferred for S2b; this correction does not alter any criterion. S2b may be published independently with lane rendering still guarded. B2 integration cannot use incomplete port geometry as a shortcut.

### #467

1. A lane row mode exists. On `02-programme-board` the 26 items occupy **at most 14 lanes**, with the chain `structure → avionics → bus-test` on one lane. The acceptance review lists the lane count and attributes every lane above 10 to its cause: a mark or label collision, or a chain rule. *(Amended 2026-09-27: was "at most 12"; see the comment.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.
