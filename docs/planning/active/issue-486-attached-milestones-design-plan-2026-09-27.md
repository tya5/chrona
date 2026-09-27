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

## Selected design and whole-architecture review

- An attached point's plot label is **required facts**, not a discretionary lane name: its title, planned date and available finish delta form one measured text request. Layout tries the declared lane placement ladder first; if none fits, it emits the complete label as `visible-overflow` with the existing layout warning, never a suppressed/partial label. Ordinary lane names retain #467's terminal suppression. The visible-overflow outcome is explicit evidence for later local tuning, not permission for Scene to choose text or for lane membership to change with Theme.
- `rows.points: own-row` controls automatic rows, as View v0.28 already declares. In lane mode, excluding `attached` from `rows.packing` restores independent membership; other declared lane rules may still group that point. This is the lane analogue, not a hidden `points` compatibility mode. Explicit rows remain author-controlled. No schema or Project migration is needed.
- Project `attachesTo` remains presentation metadata: no schedule edge, changed date, containment or relation semantics. View resolves host membership and item identity; Layout owns measured label geometry and collision outcome; Scene projects completed primitives and lane handoff; SVG serializes them. Relations/annotations use the same placed item anchors. This matches Specs 05/06/08/38 and #467's data-only membership boundary. The only normative correction is the required-facts exception in Spec 38 §3.1. Risk: fallback may visibly overlap in dense lanes; a nonessential aesthetic adjustment is a successor issue, while silent loss is unacceptable for #486.

## Next phase

Publish the implementation plan after this design and normative correction land.

Local aesthetic tuning that is not needed for these criteria belongs in a successor issue, not this record.
