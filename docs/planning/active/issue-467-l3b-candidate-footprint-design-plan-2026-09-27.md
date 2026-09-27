# Design Plan — L3b Projection-to-Lane Footprint Closure (#467)

**Public base:** L3b implementation amendment `a28793e2`. **Triggered by:** B1 implementation review of the current `ReviewProjection`/composer seam. **Amends:** [L3b preflight design plan](issue-467-494-l3b-prelayout-route-evidence-design-plan-2026-09-27.md). No product mapping or public lane activation is authorized by this plan alone.

## Published facts and gap

`_project_review` intentionally rejects lane mode before scheduling. The existing `_compose_rows` otherwise creates per-selected-item Review rows, and #486's automatic attachment fold adds a selected attached point to its host's row as a shared member. One such row may also contain a primary/combined item and comparison member. The current L3a neutral `LaneCandidate` models one mark and one required title/delta rectangle. It does not state how the full Review row's planned/actual/comparison/attached-point marks and **multiple required labels** become one atomic lane candidate, nor how the chosen lane-local frame is vertically translated into a surplus-distributed final row. Implementing that translation ad hoc would risk hidden point labels, false collision checks or row overflow.

## Design questions and slices

1. Define a canonical candidate bundle from each selected Review row: host item identity, comparison/actual members, attached child identities and their required text. Specify exactly which source facts are normalized before the final manifest and which remain post-solve. Keep source/primitive identities separate from generated lane identity.
2. Define all role-specific inline and block footprints using the same scale, Theme mark geometry, font metrics and stroke/clearance contract as final composition: planned span/point, snapshot/scenario, actual closed/open/point, missing actual, progress, attachment, icon-leading text and selected delta. State how one bundled host plus attached labels is admitted atomically to one lane, how internal collisions are treated, and how insertion stability applies.
3. Specify the lane-local frame and final row translation under `pack` and `fill`, including row padding, up to three stagger text rows, mark level and #480 table line block. The final composer must realize the preflight's selected placements without a second search or mark stretch.
4. Review #486 attachment, #480 row sizing, #481 group bands, #487 table columns, #466 obstacle/routing priority, Specifications 38/50 and automatic-mode byte preservation. Publish a design correction, living spec update and whole-architecture review. Then publish an implementation-plan amendment naming the exact B1/B2 seam and focused fixtures before product integration.

## Literal #467 acceptance retained

- [ ] A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
- [ ] Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
- [ ] Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
- [ ] Deltas remain visible for packed items that have them.
- [ ] New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
- [ ] At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

This plan adds no new acceptance. The [L3b design plan](issue-467-494-l3b-prelayout-route-evidence-design-plan-2026-09-27.md) continues to carry all three literal #494 criteria. B1 may publish an isolated typed seam with tests, but cannot claim complete candidate/attached closure until this correction and its plan amendment are accepted.
