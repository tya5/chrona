# Issue #1109: node-aware routing work record

## Published baseline and design plan

Public main: `23bc8a57` (read 2026-10-04). #1114's primary-mark safety
is the preceding lane-R slice in PR #1122 (acceptance pending).
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
authoring schema, Theme knob, terminal geometry or reviewer YAML change is intended.

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
does not justify sharing an arrival segment. The endpoint-identity requirement
and shared-approach observer cover table-timeline dependencies; dependency-network
edges retain their separate contract. Candidate comparison uses completed,
terminal-trimmed approaches. Cycles are diagnosed, not treated
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
generated mirrors/artifacts.

## Current implementation and acceptance

Implementation: shared ranked candidate selection; endpoint-preserving S-jog
reduction; stable routing order; paired Scene endpoint identity and delivery
ownership; exact-pair diagnostic observation. Incoming IDs use a compact JSON
array so opaque lane identities containing commas remain unambiguous. Synthetic
tests cover reverse declarations, multiple arrivals, mirrored endpoints, cycles
with diagnosed residual overlaps, ranking ties, mark safety and unchanged SVG
serialization when only metadata changes.

Verification: Layout/Scene focused suite 1,401 passed; after terminal-trimmed
ranking, 44 terminal/corner/node/mark tests passed. CLI aggregation test passes.
Import-direction and Scene delivery-owner gates pass. Schema-equivalence L1
passes with four reviewed additive deltas. With all 63 freshly rendered Scenes
overlaid in memory and 27 declared v0.6-to-v0.7 mapping deltas, L2/L3 have no
failures (28.43 s / 7.50 s); both versions remain validated. Schema annotation
lint passes, as do 49 identifier/viewer-fit tests. Full release acceptance still
depends on resolving the rendering gates below and a green public-head CI run.

Fresh copied-tree corpus against immutable `23bc8a57`: 63/63 materializers
complete, primary-mark crossings zero, unresolved same-node overlaps zero and
five diagnosed overlaps. Target B `launch-leop` is a straight vertical departure
with no `frr-launch` overlap or S-jog, checked in SVG/PNG. However 495/627 route
geometries change (including normalization, not 495 proven visual changes),
seven paths disappear and member labels decrease 809 → 782. Member suppression
occurrences increase 44 → 70 (36 new, ten removed, compared per context);
relation-label suppressions
increase by one. The seven missing paths match #1114's
unresolved inventory. This is not release acceptance.

Public-head [CI 37169754275](https://github.com/tya5/chrona/actions/runs/37169754275)
at `6fd5ce49` passes conformance, derived preview, MCP floor and newest-Python
reproduction of all public materializers. Pytest reports 6,841 passed, 64 skipped
and five failures: `test_halcyon_02_routed_note_trial_is_bounded_clear_and_deterministic`,
`test_slide_16_draws_shipment_campaign_without_losing_anything`, and
`test_cli_output_is_unchanged` for `render-halcyon-view-theme-scheme-layout`,
`render-halcyon-resources-png`, and `render-halcyon-emit-scene`.
Controller name recovery and suppression aggregation no longer fail.
`derived-ready` fails downstream of pytest. Preserve the real route/name gates;
review CLI golden changes only after geometry and warning counts stabilize.

Bounded read-only probes locate a coupled route/name planning problem. Reserving
all three rescue corridors replaces the lost set with `tvac-emc` and suppresses
the previously shown `pdr` name, failing both preservation gates. Reserving only
shipment's corridor also introduces lost `tvac-emc`; simple incremental corridor
acceptance is therefore **not a demonstrated fix**. Raising search bend penalty
to 1000 does not rescue shipment and introduces further losses. No such policy
change is selected or implemented. Next design question: preserve feasible
routes and names under coupled reservation/replacement, without allowing a new
loss or adding project-specific core exceptions. The old editorial `tvac-emc`
route crossed its own primary mark; its replacement is safe but changes the
joint name/corridor plan. All four missing `launch-leop` cases are lanes:
campaign/rehearsals names now obstruct the formerly safe direct route, and all
twelve alternatives exceed declared quality caps. These are coupled planning
failures, not evidence that caps should be relaxed. Programme-board's single
launch corridor can recover `launch-leop` and the `frr` name, but newly pushes
`psr-shipment` to visible fallback, so the preservation gate correctly rejects
it. Treating fallback as distinct from suppression would describe the result
more precisely but would not repair that worsened relation. A corrected
editorial trial reserving only 21 existing good corridors plus shipment
recovers detector/shipment but suppresses five names; it also remains rejected.

## Resource adaptation design and implementation amendment

A temporary Controller executive render with existing declared fallback
`[inside, above, start, end, suppress]` restores all eight names and all seven
routes without primary-mark crossings, retaining the previously visible
`bringup-to-performance` relation label. An end-first trial recovered names
but lost that label in 26 of 32 affected contexts; it is not selected.
Fresh corpus bindings locate 31 lost
`evb-arrival` names in 18 Views, not 31 separate declarations. Select that ladder
for those owning sources, preserving the original first two rungs. No Project
dates, relation identities, selection, core exception or quality cap changes.

Architecture review: View owns the permitted member-name fallback ladder;
Layout still measures and checks each candidate, including lane row/reach and
own-mark association (Spec 50 §§3.2–3.3). Scene/adapters remain projections.
This allows author-controlled presentation tuning rather than changing general
routing to satisfy one example. No public grammar or normative rule changes.
Different accepted boxes can affect routes, so name recovery alone is not
acceptance. Snapshot-label suppression in `baseline-ghosts` is separate and is
not addressed by this primary-name adaptation.

Implementation unit: `examples/controller-z/views/` sources `annotation-artwork`,
`annotation-kinds`, `annotations`, `as-of-below-plot`, `as-of-foot`,
`axis-cell-corners`, `axis-ticks`, `axis-tiers`, `capabilities`, `executive`,
`group-child-indent`, `group-tabs`, `heading`, `icons`, `in-progress`,
`text-roles`, `value-affixes`, and `viewer-fit`. Each retains its current
selection/intent; only the declared fallback ladder changes. No packaged mirror
is present. Publish this amendment before edits, then batch the 31 affected
contexts (32 total bindings) and focused Controller render/materializer tests.
Require recovered member names, no new relation-label or route loss or
primary-mark crossings, and the existing
association/overlap guards. CI supplies derived artifacts and the full release
gate. Keep the seven HALCYON route losses and separate label findings open.

Resource implementation `ec386226`; verification: all 32 affected materializers
succeed; all 225 dependency
path identities and point tuples match the prior fresh batch. Member-name
suppression occurrences fall 31 → 0, while all relation-label suppression sets
remain unchanged (28 occurrences). Primary-mark crossings, host-association
errors and row escapes are zero. Executive SVG/PNG inspected; 24 focused
Controller/label tests pass, and the public-materializer acceptance passes
against the fresh copied snapshot. The aggregation fixture also passes with
exact emitted member counts, including no aggregate when the count is zero;
it no longer requires a corpus example to lose a name. Generated files remain
CI-owned. The separate routed-note test is a genuine failure: TVAC exhausts
the 1,024-state route search and produces no leader, so its safety/association
assertions remain unchanged pending correction.

Read-only annotation diagnosis: an expanded-budget trial finds a strict route
for the same box at trial 10, identically in two renders. This is a feasibility
lead, not acceptance: it exceeds the declared 1,024-state cap and fails
placement-decision validation. Neither per-pair nor globally ranked canonical
path prefixes fit within that cap; an endpoint-interior precheck rejects no
pairs. No tested bounded search correction is selected.
Next: establish a bounded, deterministically counted connector search with a
neutral witness and exact TVAC safety checks, then publish any changed search
contract and architecture review here and in Spec 33 before product edits.
No higher production cap, obstacle waiver or selected search change exists.

## Editorial context adaptation: design and implementation plan

Select a 3200 × 900 viewport for only
`examples/halcyon-1/contexts/16-gallery-editorial-lanes.yaml` (currently 2400 × 900).
The existing slide acceptance explicitly chooses widening rather than detaching
names. A resource-equivalent Draft probe recovers all three missing editorial
relations (22 → 25 dependency primitives) with zero name/relation suppressions.
Architecture review: Specs 13 §4 and 33 §1 assign viewport to the independent
Render Context; Spec 08 §4.1 permits the resulting global reflow. Project facts,
View semantics, Theme typography, default name reach and route quality/safety
remain unchanged. No core exception, normative amendment or shared preset edit.

Implementation unit in PR #1122: change this one viewport, materialize the exact
public context in a copied tree, run both editorial slide acceptance tests and
context/schema gates, check intended relation inventory, crossings, label reach,
and SVG/PNG boundaries. CI owns derived mirrors and the full release gate.
All coordinates may change intentionally; the wider canvas is the migration.
The four other HALCYON route losses and TVAC search remain separate open gates.
