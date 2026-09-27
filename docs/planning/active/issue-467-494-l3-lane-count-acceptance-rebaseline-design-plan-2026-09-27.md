# Design Plan Amendment — Lane-count acceptance rebaseline (#467, #494)

**Public base:** `632f971411b2f283cc15f634de89143a1a2db73d`. **Source:** [#467 owner amendment](https://github.com/tya5/chrona/issues/467), observed 2026-09-27 08:42 UTC. This plan amends the [L3 completion ladder](issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md); the preceding plans and reviews are historical records, not current acceptance authority. The fresh authenticated issue body and comment supersede their old twelve-lane wording.

## Published, inferred, and unverified

- **Published:** `main` contains the neutral lane allocator, Layout geometry ownership, source-keyed facet contract and S2a review. Public lane rendering is still fail-closed. The reported remote WIP measurement at `0a035c64` was 13 lanes on 02 after a geometry fix, but is not current-main or release evidence.
- **Owner-approved:** the 02 ceiling is now 14 lanes. Every lane above ten needs an attributed cause: mark collision, label collision, or chain rule. A third label row is optional, not a prerequisite. Named-chain, required-name, and #494 route requirements are unchanged.
- **Inferred:** this acceptance change does not affect S2b's projection-to-facet mapper or the neutral stroke-envelope geometry contract; it does change L3b's pause condition and final review evidence.
- **Unverified:** current 4wd Project with the published 10× stroke envelope may differ from WIP counts. The 02 chain, complete required labels/deltas, relation causes, and 02/11/12 no-crossing gates remain unproven.

## Literal issue acceptance to preserve

1. A lane row mode exists. On `02-programme-board` the 26 items occupy **at most 14 lanes**, with the chain `structure → avionics → bus-test` on one lane. The acceptance review lists the lane count and attributes every lane above 10 to its cause: a mark or label collision, or a chain rule. *(Amended 2026-09-27: was "at most 12"; see the comment.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

The three #494 route and membership criteria remain exactly as stated in [#494](https://github.com/tya5/chrona/issues/494):

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.

## Design questions and slice order

1. Re-measure the WIP geometry as an early feasibility signal, stating its stale Project/View/code limitations. Count 02 lanes, inventory any lanes above ten by collision/chain cause, and report chain, labels, deltas and route results separately. Do not use WIP output as current-main acceptance.
2. Define the authoritative 14-lane gate and cause-inventory method in a design correction. Decide whether the third label row remains an optional deterministic candidate or is deferred; choose from rendered readability and route evidence, not from the old ceiling. Preserve the required-name/route bounds.
3. Review this correction against Specs 38/46/50, selected lane design, #466 obstacle ownership, #498 packaged defaults, and Layout/Scene/adapter boundaries. Update normative text where the old ceiling is still declared a hard gate.
4. Amend L3b/L3c implementation planning and the acceptance-review template reference. Keep S2b mapper independent of the lane ceiling. Publish design-plan, design/spec/review, and implementation-plan units serially before threshold-dependent code.

## Evidence and publication

The next independently publishable unit is this plan amendment. Then publish the selected design plus whole-architecture review and normative correction; then the implementation-plan amendment. Focused fixtures may be run early to discover feasibility, but no affected product-code decision is final until those records are published. Final L3b evidence needs exact lane membership/count, per-lane-above-ten cause records, named-chain and label/delta visibility, all relation causes, and route-label crossing results on current-main composition. CI supplies the planned full matrix; batch materializer and SVG inspection at activation.
