# Design Plan Amendment — Rule-based lane acceptance (#467, #494)

**Public base:** `e80027c7c42386ddf26c9c7692b1f448d805ace8`. **Source:** [#467](https://github.com/tya5/chrona/issues/467), owner amendment observed 2026-09-27 08:56 UTC. **Supersedes:** the numerical gate plans [fourteen-lane rebaseline](issue-467-494-l3-lane-count-acceptance-rebaseline-design-plan-2026-09-27.md) and [implementation amendment](issue-467-494-l3-lane-count-acceptance-implementation-plan-amendment-2026-09-27.md). The unpushed local `b02f27d1` implementation-plan draft is not published authority and will not be pushed unchanged.

## Baseline and design questions

Published main has S2a source-keyed facets and a fail-closed public lane mode; S2b is paused for an independently identified semantic-port host invariant, whose design/Spec correction is published. The WIP branch generated 13 lanes but lacked the named chain and measured route causes. Neither 12 nor 14 is a current acceptance limit. The owner now requires two rule checks from rendered Scene footprints, not a lane-count optimization target.

Design must settle (1) how a pairwise whole-lane move is measured from Scene geometry while preserving group isolation and explicit chain exceptions, (2) how source-keyed facets and intentional overlays are counted in a per-date overlap statistic, (3) what “lower bound” means when staggered text is two-dimensional, (4) what exact gap evidence the acceptance review must report, and (5) which tests run on direct hidden Scene versus published materializers. Review against Specs 38/46/50, the #466 obstacle contract, View v0.27, Theme/icon geometry, Layout/Scene/adapter boundaries, and #494 route obligations. A numerical threshold or forced third label row must not re-enter implementation through an old plan.

## Literal issue acceptance

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

## Sequence and evidence

Publish this design plan first. Then publish a selected design correction, normative Spec 38 update and whole-architecture review. Next publish an implementation-plan amendment removing all 12/14 pause conditions and defining independent S2a port, S2b mapper, B2 Scene rule proof, B3 route and L3c activation units. Existing numerical/cause-trace design remains historical; only portions needed for source-keyed diagnostics survive after review. In B2, prove the exact named chain and both new row-1 checks on direct current-main Scene; in L3c repeat them on committed rendered Scene/SVG. Batch public materializer and generated-diff checks; let CI supply planned full matrix. Do not treat WIP as release evidence.
