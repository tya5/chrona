# Issue #1109: node-aware routing work record

## Published baseline and design plan

Public main tracked: `ba90f480` (2026-10-04); comparison baseline: `23bc8a57`.
#1114's primary-mark safety
is the preceding lane-R slice in PR #1122 (acceptance pending).
Authority: [#1109](https://github.com/tya5/chrona/issues/1109), Spec 50 §3.3,
#1084/#1072's side-entry rules, #1059's non-reversal invariant. WIP `e2529728`
is reference only: side deprioritization is not proof of actual-segment clearance.

Baseline routing evaluates relations in declaration order and accepts the first
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

The three CLI cases differ only by the absence of the now-unnecessary
`I_LAYOUT_PLOT_LABELS_SUPPRESSED` and `W_LAYOUT_LABEL_SUPPRESSED` records;
arguments, exit status, stdout, artifact descriptors and the remaining warning
are unchanged. `8623fb06` removes only those six obsolete records, not a bulk
re-recording. Six focused checks and CI confirm the correction; current CI is below.

Selective rescue-corridor and bend-penalty probes introduced other path/name
losses and are rejected. The declared resource adaptations below recover the
seven losses without a project-specific core exception or relaxed quality cap.

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

## Annotation search correction: design, architecture review and implementation plan

Use cases: a strict local route hidden behind many rectangle-blocked candidates;
an optional note index competing with its own already-selected required leader;
multiple eligible egress/box-edge pairs sharing one connector budget.
Select interval compilation of the existing finite orthogonal corridor families,
not a higher cap or a second fallback router. Omit a candidate only when a
rectangle-interior collision is proven using the exact obstacle tolerance and
named-port exemptions. Non-rectangles, stroke clearance, pending box/tail,
complete source egress, route quality and as-of partition still require exact
validation. Boundary contact and sub-tolerance penetration are not collisions.

Layout prepares finite row descriptors from eligible pairs and local envelope
axes, ordered analytically by actual compact route rank. Merge descriptors by
bends, length, source/target order and original-coordinate ties; materialize only
the popped completed candidate. Charge every materialized path once, including
duplicates, against the shared 1,024 connector budget across pairs and box trials.
Do not charge validation again or reset per pair. Input-derived interval/row
preparation is separately observable finite setup work, not covered by that cap;
do not describe it as 1,024 primitive operations. If a frontier implementation
prefetches charged paths, drain them before reporting exhaustion. A valid charged
prefix is a fit; no fit is exhaustion only when candidates remain unproduced.

Commit the selected required leader and ports into the monotone inventory before
placing its optional note index. Rejected provisional candidates leave no residue;
the index may move or suppress independently, never invalidate a required leader.
Do not relabel visible index text as non-required to evade intersection tests.

Architecture review: Spec 33 §§8.1a–8.2 and #466 C3 own these decisions in Layout;
Scene and adapters remain completed projections. Single-pair and multi-port
consumers share one private corridor engine and the existing exact obstacle and
quality validators. No Project/date, View/Theme grammar, cap, safety or fallback
waiver. Current main's #1117 role diagnostics and #1126 contrast opt-in alter no
geometry rule here; repository contrast evidence still uses its explicit registry.
Migration: candidate order/count and optional index placement may change; retain
all required content and publish intended Scene/SVG changes, not byte identity.

Implementation unit in PR #1122: private `annotation_corridors.py` engine;
`annotation_topology.py` single-pair wrapper; `annotation_search.py` merged-pair
consumer; `surface_annotations.py` leader-before-index ordering. Neutral tests
must cover exact-clear family preservation, epsilon contacts, transposed and
degenerate rank order, non-rectangles, explicit ports, cap draining/exact-last
candidate, and a global multi-pair budget. Keep the original strict TVAC test.
Run annotation focused tests, then batch affected public materializers and inspect
required content, decisions, Scene/SVG/declared-font PNG and intended differences.
CI supplies full release gates. Publish this correction and Spec 33 before code.

Disposable proof, not implemented acceptance: 205 exhaustive neutral cases keep
every exact-clear candidate, including half-tolerance rectangle-edge anchors.
The unchanged 2,100px TVAC test passes twice after interval pruning and atomic
leader-before-index registration: box trial 10, 766 paths materialized, 763 unique
frontier entries and 748 exact checks. The production rank/accounting boundary
tests and public artifact review remain mandatory before accepting the correction.

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

Implementation `2ba83810`; exact copied-tree public materializer succeeds.
Both slide acceptance tests pass on that fresh Scene: 25 dependency primitives,
all names present, no name/relation suppression and every name within default
reach. Every dependency source appears in SVG; perceptibility reports no errors
or warnings. Declared-font PNG/SVG inspected, including shipment and the recovered
structure/detector connections. The requested 3200 × 900 viewport produces the
declared overflow canvas 3200 × 2140, without cropping required rows. Schema and
Render Context focused tests: 61 passed. Generated evidence remains CI-owned.

Main reconciliation `8ebed2a0` preserves #1105's terminal-run resolver and
#1114's primary-mark arc guard. The terminal-run test now reserves its actual
final leg, avoiding an assumption about the old short-stub routing order;
68 terminal/node/mark/routing tests pass. Exact editorial materializer bytes
remain identical after reconciliation. `29efd023` additionally tracks main's
bot-derived terminal-none evidence. Required release CI remains pending. The
CLI correction is verified; the lane resource slice below recovers the four
remaining HALCYON paths. TVAC and literal route preservation remain open.

## HALCYON lane resource adaptation: design and implementation plan

Use case: retain all selected names and semantic paths under mark-safe routing.
Select a 3200 × 1080 viewport for Contexts `02-programme-board`, `12-glyph-gates`,
`19-gallery-text-compression` and `20-gallery-vertical-group-tags`. In the three
owning Views (`02-programme-board`, `19-gallery-text-compression`,
`20-gallery-vertical-group-tags`), select label side `start` and the existing
fallback ladder `[start, end, above, below, suppress]`. Both changes form one
resource unit: width alone lost names, and fallback alone did not recover paths.
The shared `02` View also serves `11-overlay-briefing`; retain that Context's
2560 × 1560 viewport and include it in verification.

Architecture review: Specs 13 §4 and 33 §1 assign viewport to Render Context;
Spec 50 assigns the finite name-side ladder to View and geometry, row/reach,
association and collision checks to Layout. No Project/date, Theme, core rule,
quality cap, annotation search budget, grammar or reviewer resource changes.
The published #1126 opt-in contrast design changes no selection here; verify
these outputs with the current explicit legibility floors, not relaxed defaults.
The migration intentionally reflows paths and names; do not claim byte identity
or completion of #1114's separate compliant-route preservation criterion.

Disposable public materializers for all five bindings succeed: each has all 24
dependency paths and all 26 names, with no new route/name/relation-label/index
loss against immutable main `06603a02` or the earlier fresh corpus. Four missing
`launch-leop` paths are recovered; the four widened contexts also recover the
TVAC note index. All four widened SVG/declared-font PNGs were inspected.
The perceptibility check has no errors or warnings (contrast warnings below are
separate). Even at unchanged width, `11-overlay-briefing` intentionally changes
16 of 24 route point tuples through the shared View migration while preserving
all 24 routes and 26 names. The diagnosed Avionics shared approach
remains informational, as permitted by the literal diagnostic alternative.
Each widened context additionally reports four calendar-decoration contrast
measurements unsupported over the existing translucent launch-window band
(October 23/24/30/31); Spec 46 §8 classifies these as decoration observations,
not legibility failures. Keep these warnings visible; do not weaken paint gates.

The controlled `halcyon-two-surfaces` gallery pair must keep identical declared
environments (#354): also widen `10-gallery-network-wallboard` to 3200 × 1080.
This is a Render Context resource correction, not a gallery-validator exception.
Verify the network public materializer and comparison inventory/determinism guard.
The station-note regression must assert retained text/box and valid chosen-tail
evidence; a now-successful earlier candidate must not require the old fallback
warning. Keep fallback warning behavior covered by synthetic blocked fixtures.

Publish this design before the source edits. Then reproduce all five lane
bindings, verify inventories and geometry guards, run focused View/Context and
lane/name tests, and compare intended source changes. CI owns generated mirrors
and release tests. Accept this slice only with no new user-content loss; keep
the exact 2100px TVAC integration test and literal issue release gates open.

Implementation follows published design `84aed166` (public base `80c05ecb`).
All seven source files match the verified materializer inputs byte-for-byte;
no core change occurred between that batch and implementation. Reuse those
fresh outputs rather than duplicate the SVG batch. The new five-binding Scene
and SVG regression checks pass: declared dependency inventory, actual name
strings, two-em own-mark reach, existing note indices and perceptibility gates.
View schema, exact Context references, lane subtracks and label tests: 104 passed.
The unchanged 2100px TVAC test passes with the corridor correction above.
Implementation review found no Project, Theme, core, generated or reviewer-resource
edits. [CI 37175354474](https://github.com/tya5/chrona/actions/runs/37175354474)
has 6,875 passed, 65 skipped and three failures: strict TVAC, stale station-note
fallback expectation and the gallery-pair environment mismatch (also conformance).
All three belong to this PR and are addressed by the corrections above; no release
acceptance or closure. Main `6b795c88` is reconciled without conflicts in `116c790e`.
Public-head CI and the separate literal preservation review remain pending.

Corridor implementation `352e7878` follows pre-code publication `ce3b9766`: one shared
descriptor engine, charged on pop; exact whole-route guards; required leader
registration before optional index placement. Disjoint direct/elbow/two-/three-
bend families prevent zero legs and duplicate paths. Neutral evidence covers
198 exhaustive cases, epsilon contacts, both orientations, fractional/large
coordinates, global rank and a real 17-candidate prefix, non-rectangles/ports,
exact-last fit and true exhaustion. Focused annotation/balloon/inventory/gallery
tests: 72 passed; node/port/search set: 35 passed; unchanged strict TVAC: passed.
Review retains the finite two-unit envelope-offset grammar and exact validation
of declared clearance; it does not promise every continuously feasible route is
in that finite family. Setup cost depends on pairs, axes and obstacles, not just
the path cap; no global feasibility or constant-work claim is made.

All six affected timeline materializers succeed; five lane Scene/SVG guards pass.
Compared with the prior reviewed resource batch, the four widened SVGs and
Editorial SVG are byte-identical. Overlay's only primitive changes are the
window-note rectangle becoming a balloon and its added strict leader; all
existing dependency paths, names, relation labels and note indices remain.
Declared-font PNGs inspected for programme-board and overlay; the unchanged
SVG groups reuse their previous visual review. No perceptibility or contrast
errors; the four decoration observations per widened context remain visible.
The corrected network Context materializes with unchanged inventory (16 nodes,
11 rendered edges, 17 text primitives); every primitive/edge source is in SVG,
and diagnostics are empty. Inventory/gallery guards: seven passed; the real
inventory tool validates 64 slides and 13 gallery links. Station-note text/box
and its single tail remain; its existing optional index suppression is unchanged.
No repository-derived outputs, Project facts, Theme or reviewer resources edited.
PR CI at `89dacde6` passes all three pytest shards, conformance and public
materializer reproduction ([run](https://github.com/tya5/chrona/actions/runs/37178299268)).
Main's published #1074 actual-gate default is reconciled without changing its
contract; mark-safety, entry and symbol-geometry tests pass (34 tests). Because
enlarged actual symbols can change comparison-host corridors and nearby labels,
new public-head CI and #1114's literal compliant-route preservation remain required.
