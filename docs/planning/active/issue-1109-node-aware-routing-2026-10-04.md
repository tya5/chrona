# Issue #1109: node-aware routing work record

## Published baseline and design plan

Public main: `23bc8a57` (read 2026-10-04). #1114's primary-mark safety
is the preceding lane-R slice, published as PR #1122 (implementation pending).
Authority: [#1109](https://github.com/tya5/chrona/issues/1109), Spec 50 §3.3,
#1084/#1072's side-entry rules, #1059's non-reversal invariant. WIP `e2529728`
is reference only: side deprioritization is not proof of actual-segment clearance.

Current routing evaluates relations in declaration order and accepts the first
eligible port pair. It has no node-level incoming-approach check or S-jog
simplification. Published target B's reported geometry remains to be remeasured.

Literal acceptance:

> - A gate with one incoming relation from the left at mid-height and one outgoing relation to a successor below: the outgoing path shares no segment with the incoming path's final segment.
> - The S-jog fixture: the route has the minimal bend count for its entry.
> - A corpus Scene check reports any two relations at one node that overlap along a segment. It must be 0 after regeneration, or every remaining case is listed with a diagnostic.
> - Target B: `launch → leop` leaves the gate without overlapping `frr → launch`, with no S-jog.

Use cases/review questions: declaration-order independence; several incoming
edges; point and mirrored span endpoints; blocked egress; cycles; orthogonal
S-jogs with and without a free collapse; fixed semantic endpoints and terminal
stubs. Decide whether to reserve natural incoming sides or use completed
approach segments, how to resolve cyclic placement deterministically, and how
bend preference interacts with side-entry and safety. No new Project data,
schema, Theme knob, terminal geometry or reviewer YAML change is intended.

## Publication and implementation boundaries

Publish this design plan before selecting the behavior. Complete design,
whole-architecture review, normative change and implementation plan here in
place, then publish before code. Keep one coherent routing PR when the changes
can be verified together; do not split local adjustments into additional PRs.

Likely owners: Layout `routing.py` and `surface_routes.py`; Scene perceptibility
observation and diagnostic sentences. Focused synthetic tests must prove the
four criteria, entry and mark-safety preservation, reverse declaration order,
cycles and blocked alternatives. Batch corpus Scene/SVG evidence once per
completed behavior; full release tests remain in CI. #1108's endpoint nudging
and dev B's #1105 terminal module are excluded.

Current status: design plan published; selected design/implementation pending.
