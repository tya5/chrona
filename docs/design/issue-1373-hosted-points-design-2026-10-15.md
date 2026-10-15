# #1373 row 3: physical point hosting

Design candidate; not implementation authorization until the architecture review
and implementation plan are published. [Plan](../planning/active/issue-1373-hosted-points-design-plan-2026-10-15.md).
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
  All candidate/recovery and annotation callers consume the same typed link.
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
  by final composition. This structural change requires explicit unit coverage
  before the implementation plan is finalized; it is not a post-render patch.
- Scene emits ordinary completed marks/text/routes. Adapters do not place,
  fit, infer hosts or change dates. The existing actual-ground contrast gate
  remains enforced for point and bar; no automatic recolouring or exemption.

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

Open architecture decision: choose the minimal facet-allocation record that
preserves existing subtrack and visible-emission invariants, and specify the
failure for two fixed hosted glyphs that physically collide. Do not finalize
implementation planning until that decision is reviewed. A draft is not a
completed design or permission to change product code.
