# #486 attached milestones — current work record

**Public base:** `0d0dfef4` (`main`, 2026-09-28). **Authority:** [issue #486](https://github.com/tya5/chrona/issues/486), [Project spec §9.1](../../specification/05-project-format.md), [Review-row spec §3.1](../../specification/38-review-row-composition.md). Earlier [design](../../design/issue-486-attached-milestones-design-2026-09-27.md), [architecture review](../../reviews/current/issue-486-attached-milestones-architecture-review-2026-09-27.md), and [implementation plan](issue-486-attached-milestones-implementation-plan-2026-09-27.md) remain background; this record holds the current plan.

## Published baseline

`attachesTo` validation, schedule independence, automatic-row placement and `points: own-row` are implemented. #467 is merged: View v0.28 lanes assign an attached point to its host lane and Layout tries the host subtrack first. There is no committed two-gate example or rendered lane-mode acceptance test. Lane labels may currently suppress an attached point's required facts; that conflicts with #486's visibility criterion. The issue comments predate #467's data-only lane contract and do not establish acceptance.

## Literal acceptance

1. “The Project schema accepts `attachesTo` on point objects; the validation errors and the outside-span warning are covered by tests.”
2. “Attachment changes no scheduled date. A test compares schedules with and without it.”
3. “A View draws an attached milestone on its host's row, both with and without #467 lanes, and `points: own-row` restores its own row.”
4. “The milestone's name and date stay visible, and its delta if it has one.”
5. “One committed example has a long task with at least two intermediate milestones attached. HALCYON-1's `campaign` or `mcs` would serve.”

## Design closure before product code

- Reconcile required attached-point facts with #467's lane-name suppression rule. Decide whether a lane attached-point fact label is a distinct required label, how Layout reserves/places it, and the diagnostic if it cannot fit. Do not introduce Theme-dependent lane membership or move text decisions into Scene.
- Clarify `points: own-row` for automatic rows and the lane-mode equivalent (omitting `attached` from `packing`); check the literal criterion against View v0.28 schema and document any intended migration.
- Review the chosen rule against Project scheduling, Review Item identity, View ownership, Layout geometry, Scene projection, adapter output, relation/annotation anchors, and the public materializer corpus. Update the living spec and this record before implementation.

## Publishable slices and evidence

1. Publish this current design plan.
2. Publish the selected visibility/opt-out contract and whole-architecture review here and in the normative Review-row spec; amend the implementation sequence below.
3. Implement only the missing lane/label behavior and rendered tests. Reuse existing attachment validation and automatic-row code unless tests reveal a defect. Focused tests must cover a host lane, two children, title/date/delta visibility, automatic `own-row`, and lane packing opt-out.
4. Add two intermediate gates to HALCYON-1 `campaign`, repin immutable Project references, regenerate public Scene/SVG evidence in one batch, and inspect changed SVG plus unexpected diffs. Run focused tests locally; CI supplies the three-OS full suite and newest-Python materializer check. Publish an acceptance review with a row and direct evidence for each criterion; close #486 only after CI and rendered evidence pass.

Local aesthetic tuning that is not needed for these criteria belongs in a successor issue, not this record.
