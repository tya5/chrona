# Design Plan — Pre-layout Lane Reservation and Route Evidence (#467, #494)

**Public base:** `main` at `1cc86e1f` (L3a neutral allocator); L3a CI and acceptance review remain pending. **Amends:** [L3 publication ladder](issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md). **Issue authority:** [#467](https://github.com/tya5/chrona/issues/467) and [#494](https://github.com/tya5/chrona/issues/494). This is a design gate before L3b product integration, not evidence that lane mode is publicly usable.

## Published facts, inference, and unknowns

Published code normalizes semantic table cells, measures sources, computes `timeline_content_block_requirement`, resolves content height and solves the viewport **before** `normalize_v05_surface_content` and `compose_surface_layout`. The current requirement function uses ordinary row extents and a table text line block; it cannot know a later lane allocator's three staggered label rows. The composer currently derives row/group geometry, mark tracks, labels and routes in one coordinate phase. `RelationPlacement` has suppression and a generic diagnostic but no typed failed-attempt evidence. The route loop drops egress, search and quality rejection causes. Relation labels are intentionally anchored to completed paths after routing; required lane item names and deltas, not relation labels, are the pre-route obstacles.

The inferred gap is a missing Layout-owned, geometry-free pre-layout lane reservation whose exact immutable result is consumed both by content-height solving and coordinate composition. The route gap is the missing rule for classifying multiple failed port pairs and transporting measured causes without Scene or adapter inference. It remains unverified that the L3a allocator's current interface covers every attached-point and comparison footprint in all selected public contexts; focused integration probes must establish this before activation.

## Literal issue acceptance to preserve

### #467

- [ ] A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
- [ ] Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
- [ ] Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
- [ ] Deltas remain visible for packed items that have them.
- [ ] New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
- [ ] At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

- [ ] On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
- [ ] `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
- [ ] Lane count and lane membership on 02 are unchanged, or any change is attributed.

The separate [Editorial/default design plan](issue-467-498-editorial-lane-default-design-plan-2026-09-27.md) owns the #467 fifth-row decision; L3b cannot resolve it by silently changing a catalogue entry.

## Design slices and questions

1. Define a Layout preflight input from selected Review item/group intent, semantic table/surface facts, measured font assets and Theme metrics. Decide whether the L3a neutral allocator can be reused unchanged or needs an immutable planning wrapper. It must not depend on solved viewport coordinates or route geometry.
2. Define the immutable result: canonical lane membership/identity, item footprint and chosen label ladder, reserved lane and group block extents, table summary facts, required label bounds/anchor intent, and validation invariants. Specify a conservative finite reservation for label rows so a later collision choice cannot increase the preflight extent. `timeline_content_block_requirement` and composer must consume **the same** result, not run independent allocation algorithms.
3. Specify lane table measurement and allocation order against #480 text extents, #481 group bands, #487 measured columns and #486 attached points. Preserve source-item identity and explicit/automatic bytes. Determine whether `TableContent` remains a geometry-free input or a Layout-generated summary; no View or adapter should assign lane geometry.
4. Define route attempt facts and final suppression cause aggregation across all endpoint port pairs. Preserve the existing bend/detour policy, zero required-label crossing, and diagnostic stability for non-lane outputs. State which per-relation counts and quality measurements are required to prove #494.
5. Clarify phase order: required lane item names/deltas and other phase-1 required obstacles precede semantic routing; route-anchored relation labels and optional labels can remain after completed routes. No rule may allow a route through a required name merely to satisfy a count.
6. Review against Specifications 38 and 50, the #466 route-priority correction, #467 selected and feasibility designs, and #480/#481/#486/#487 contracts. Record alternatives and migration impacts. Update living specifications and a whole-architecture review before finalizing an L3b implementation amendment.

## Evidence and publication ladder

Publish this plan first. Next publish a design correction, Specifications 38/50 updates and whole-architecture review as a coherent design unit. Then publish an implementation-plan amendment with file owners, hidden-path tests, public materializer characterization, generated-diff gate and CI boundary. Only then modify L3b product code. If the preflight requires final route or viewport geometry, return to design and select a declared iterative solve or conservative bound; do not hide the cycle in `render_review` conditionals.
