# #1373 row 3: physical point hosting

Selected design; [architecture review](../archive/reviews/issue-1373-hosted-points-architecture-review-2026-10-15.md)
and [implementation plan](../archive/planning/issue-1373-hosted-points-implementation-plan-2026-10-15.md)
are published. Implementation follows merged #1397 row 3 (PR #1523).
[Design plan](../archive/planning/issue-1373-hosted-points-design-plan-2026-10-15.md).
Authority: [reviewer boundaries](https://github.com/tya5/chrona/issues/1373#issuecomment-6184233415).

## Contract

Layout Profile `reviewSurface.marks.points.host` is optional, with the sole
opt-in value `span-when-inside`; omission disables physical hosting. Add it in
place to v0.10 (Spec 56). Normalize once into a typed Layout policy; an omitted
policy preserves canonical manifest and rendered output. No View, Project or
Scene schema extension, row-packing change, preset-ID switch or compatibility alias.

Projection retains declared Project `attachesTo` separately from derived
`attached_to`, and carries direct Project parent for Primary, Snapshot and
each Scenario. Preserve these facts through explicit/comparison/lane projection.
Actual uses its owning Project's links, never a different comparison Project's.
Hierarchy validation and scheduling semantics remain unchanged.

For each admitted point facet, resolve the declared attachment first, then the
direct parent. A candidate must be a selected, drawable span facet from the same
source kind and scenario identity, with the same temporal facet. Test the point
date against the candidate's original semantic interval, inclusively. Never use
half-open lane-packing intervals or clipped paint bounds for this test. A candidate
without a drawable span, including hidden rollup and folded-header-only marks,
does not qualify. Missing-Actual placeholders are not observed point facets.

When a target has multiple occurrences, prefer its unique occurrence in the
child's review row. Otherwise require one eligible occurrence across the selected
source. More than one eligible occurrence is `E_LAYOUT_POINT_HOST_AMBIGUOUS` at
`/projection/items`, naming the child and candidate identities; do not guess by
declaration order or parse placement IDs. An ineligible attachment permits a
qualifying direct parent. If neither qualifies, preserve the original point.

## Completed geometry and identity

Hosting preserves the point's date-derived inline centre and Theme-selected
size/shape, and centres it on the completed host span's block axis. It does not
shrink the glyph, move its date to clear a capsule end, or clip it to the bar.
Thus a point at an inclusive endpoint may protrude beyond the bar; this is not
a different date. Authors tune symbol size, ink and outline in Theme YAML.
Layout completes its paths, parts, ports, footprints and window records together.
The point draws above its exact host: completed paint order is at least the
host's order plus one; unrelated marks retain their declared order.

Keep the child's placement/source/provenance and semantic row/lane/member IDs.
Record a separate typed physical-host relationship containing exact point and
host placement identities and the host's physical row. This is not the restricted
text paint-host field. Resolve hosting before obstacle seeding, label placement,
relation planning and Scene projection. Excluded window facets cannot be revived;
the View's half-open window admission is independent of inclusive host eligibility.

## Downstream connections

- Plot labels follow the completed point in its physical host row, using that
  row's placement band for candidates and association. Their semantic row and
  provenance stay the child's. Table cells and row ordering do not move. Reuse
  existing suppression/overflow diagnostics; no mandatory duplicate label.
- Relation and annotation endpoints keep the point's semantic port. Extend the
  existing finite egress mechanism with only its exact resolved span host. That
  host may be crossed on the recorded endpoint-to-exposed-boundary corridor,
  never on the route body. Comparison siblings keep their existing eligibility;
  do not insert a different object's span into generic comparison clusters.
  If a span endpoint itself is covered by its exact hosted point (notably an
  inclusive start/end milestone), the same link permits egress through that
  covering point only on that endpoint corridor. A different hosted point not
  covering the endpoint gains no exemption. All candidate/recovery and
  annotation callers consume this reciprocal, endpoint-local relationship.
  Keep physical corridor authority separate from `ConnectorEgress.host_ids`,
  whose legacy consumers also use it for route-body checks. Add an immutable
  `corridor_host_ids` field and an explicit union used only when validating
  the semantic-to-exposed segment. The legacy field retains its comparison
  meaning. Physical neighbours affect exposed-boundary geometry, not generic
  comparison connectivity. Full-path validators split segments at the recorded
  exposed boundaries: only the contained endpoint portions receive physical
  authority, even after collinear reduction or terminal setback. Body portions,
  corner arcs and fanout extensions receive none. Relaxed recovery must retain
  physical hosts as obstacles, not discard them as non-endpoint marks. Hint
  reanchoring and annotation validation consume the same recorded corridors.
- Lane closure still accounts for exactly one child facet. Preflight needs an
  explicit separation of semantic ownership from physical allocation: the
  current whole-instance subtrack unit cannot represent independently hosted
  planned/Actual facets. Resolve a typed point-facet-to-span-facet relation once;
  the host's physical allocation owns that point facet's footprint and label
  demand, while its original child remains the semantic emission owner. Compute
  the point's host-relative block offset in the zero-origin host frame and reuse
  it after allocating that host's physical row/subtrack. Do not allocate a second
  copy in the child's row or call it window-omitted. Remaining unhosted child
  facets retain their original physical allocation.
  Separate allocation records from original facet/emission records rather than
  broadening `overlay_with` across semantic lanes. Only each resolved child/host
  pair may intentionally overlap; unrelated points retain collision checks.
  Preflight must prove the same physical bounds and exact overlap pairs emitted
  by final composition; it is not a post-render patch. See the allocation
  contract below.
- Scene emits ordinary completed marks/text/routes. Adapters do not place,
  fit, infer hosts or change dates. The existing actual-ground contrast gate
  remains enforced for point and bar; no automatic recolouring or exemption.

## Facet allocation contract

One immutable resolved host plan joins original selected child/host occurrences
and facets before packing. It has no coordinates and performs no row assignment.
Window admission is an explicit input; final composition consumes that same plan,
not a second heuristic host search. Non-lane composition uses the same resolver.

Keep the original semantic footprint inventory intact. Derive an allocation-only
inventory by moving each hosted facet's glyph parts and mark-bound visuals to its
host span's allocation unit, translated into the host's zero-origin frame. Each
source facet occurs exactly once across the derived units. The child keeps its
semantic lane and its remaining facets; a unit with no remaining physical facets
is admitted only by the explicit hosted-facet account, never by pretending it was
window-omitted. Existing unhosted inputs keep their allocation and order.

Pack each host assembly as a unit. Add only exact host-mark/hosted-mark overlay
pairs to that unit; preserve existing compound-paint overlays, never grant a
child/child or icon/text blanket exemption. Two hosted glyphs that cannot occupy
their fixed truthful positions without an undeclared collision fail with
`E_LAYOUT_POINT_HOST_OVERLAP` at `/projection/items`, naming both identities.
Do not hide a point, change its date, or move it to another host subtrack.

The result retains semantic instance tracks and adds a source-facet-to-physical-
frame map. Final composition uses the host's allocated track origin plus the
same zero-origin facet offset; no absolute cross-lane offset is guessed before
row allocation. Labels retain their semantic owner but their measured demand
and candidate band use the resolved physical row. Original/final inventories
must prove identical facet IDs and translated footprints. Validators compare
against this physical map while preserving semantic lane emission accounting.

This separates allocation from ownership inside Layout; it does not relax the
existing same-lane `overlay_with` rule on the semantic inventory. The no-policy
path does not build or consume a physical-host map.

## Alternatives and migration

Do not implement this through `rows.points`, `parentRow`, predecessor attachment,
Scene transforms, a route-wide host exemption or a Project-specific condition.
Those either change membership or split ownership. Existing resources need no
migration because the policy is off. Opting in may move points and plot labels,
change their routes and expose contrast failures; disclose those intentional
changes in the PR. No public materializer changes are expected without opt-in.

## Architecture review questions

Verify source-link provenance, occurrence ambiguity, explicit-window records,
lane preflight and canonical emissions, folded/hidden hosts, physical label
bands, every connector egress caller, and actual adapter output. Acceptance
must include cross-row parent hosting with labels and dependencies enabled,
not only a point already sharing its host's row.

The physical allocation contract resolves the earlier preflight gap. Review its
partition proof, exact overlap authority and final-frame equivalence before
publishing the implementation plan. A review is not evidence of implemented code.
