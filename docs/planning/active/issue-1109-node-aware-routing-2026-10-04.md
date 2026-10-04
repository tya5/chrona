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

## Selected design and whole-architecture review

- Route arrivals before departures in stable topological order; cyclic
  remainder keeps declaration order. Emit placements in declaration order.
  Compare actual completed incoming approach segments at the resolved source
  instance, not guessed natural sides or arbitrary overlapping paths.
- Select eligible paths in tiers: no incoming-approach reuse first, declared
  side entry next, fewer bends then length then stable candidate order. If only
  a conflicting eligible route exists, retain it with a relation-keyed
  `I_LAYOUT_RELATION_NODE_APPROACH_SHARED` diagnostic; final pair inspection
  also diagnoses unresolved cyclic ordering. No mark/label safety exemption.
- Collapse obstacle-free interior S-jogs before quality evaluation. Preserve
  semantic endpoints, entry/exit directions and terminal runs. Never nudge a
  route endpoint (#1108 remains separate). Recheck self-overlap and mark safety.
- Transport resolved node identity as optional `fromInstanceId` and
  `toInstanceId` on dependency Paths in live Scene v0.7 (added in place).
  Layout supplies opaque identities; Scene copies them; the observer compares
  identities and segments. Do not parse primitive/port IDs or infer identity
  from proximity. Serialize such Scenes as v0.7. Scene v0.6 is unchanged.

Architecture review: Specs 09/33 keep routing and measurement in Layout;
Spec 08 carries completed identity, not routing intent; adapters ignore the
identity metadata and draw unchanged geometry. Spec 56 permits additive live
schema fields in place. This corrects Spec 08's unimplemented public-port-ID
promise with the identity actually needed by consumers. Spec 50's bounds,
#1114 mark safety and #1059 non-reversal remain mandatory. Side-entry preference
does not justify sharing an arrival segment. Cycles are diagnosed, not treated
as a scheduling error. No Theme, View, Project or Layout Profile change.

## Implementation plan

One coherent implementation unit in PR #1122: Layout routing/selection and
resolved endpoint identity; Scene model/projection/serialization and live
schema; observer and diagnostic sentences; synthetic tests. Keep one current
record. Use grouped corpus evidence and the existing PR/release pipeline.

Acceptance evidence: incoming/outgoing chain in both declaration orders;
multiple arrivals; mirrored endpoints; blocked egress and cyclic residual
diagnostics; S-jog free/blocked and fixed endpoints; serialized identity/schema
and same-node versus different-node observations; all existing entry, mark and
label guards. Batch regeneration reports each residual overlap with its
diagnostic and rendered target B. Any broader regression returns to this
design before acceptance. CI runs full tests and schema-equivalence; no manual
generated mirrors/artifacts. Current status: design and implementation plan
published; code and acceptance pending.
