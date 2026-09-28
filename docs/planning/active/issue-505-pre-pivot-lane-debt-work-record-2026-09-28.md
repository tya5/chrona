#505 — pre-pivot lane debt: current work record

## Published baseline and design plan

`main` at `bbe6734f` is the base. #467/#494 are closed, but their release
review overstates the three-slide route test: the existing Scene intersection
assertion covers 02 and 12, not 11. Specification 38 already makes lane
membership data-only and retires the geometry-first pairwise gate. The
geometry allocator/preflight and Scene audit remain in source; their product
reachability and the current uses of each Scene field must be checked before
deletion. No unpublished branch is an acceptance baseline.

Literal issue acceptance:

1. “Every item above is either removed or kept with a named current consumer and a one-line purpose in code or spec.”
2. “No Scene field remains in the public schema without a consumer or a documented purpose.”
3. “`staged_modules.txt` lists no lane module whose stated condition is already met.”
4. “The 02/11/12 route-versus-label check exists as a Scene-level test, and the review cites the real test names.”

Design questions, in order: which `laneMode`, `laneMembers`, `laneObstacles`,
and `laneClearance` values still serve the current Scene evidence contract;
which allocator/preflight types are used by the live fixed-membership path;
whether the unused audit should disappear; and what narrow reachability
guard prevents a second test-only public entry point. Check against Specs
38/49/50, Scene v0.6 serialization/schema, the #494 route contract, and
public materializer byte evidence. Preserve live lane footprint/subtrack
ownership and avoid a gratuitous Scene version change.

The next independently publishable unit is a design and architecture decision
with an exact consumer/removal inventory. After that, publish the implementation
plan, remove only unreachable code and stale staging, add the three-context
Scene assertion and focused gate, then review the literal rows against current
public artifacts and CI. Any changed Scene schema or generated evidence must
ship atomically with its producer and serializer.

## Selected design and whole-architecture review

Keep Scene v0.6 intact. `laneMode` distinguishes a fixed-membership Scene;
`laneMembers` is the public Project/View-only membership and exact primitive
ownership oracle (`test_public_lane_layout_projects_fixed_membership` and
`test_readable_defaults` consume it); `laneObstacles` is the typed, Layout-
completed visible-footprint inventory checked against emitted primitives by
`SceneSurface` and serialization; `laneClearance` is the serialized tolerance
for interpreting that inventory, validated by serialization and used by the
Scene-level route/label test. This is current release evidence, not the retired
pairwise non-redundancy audit. Document these purposes at the public schema.
Removing fields would need a new Scene version and migration for evidence that
is still consumed; that would add churn without improving ownership.

Remove the test-only `lane_audit` and the geometry-driven allocation/preflight
entry points. The fixed-membership path still uses `LaneInlineFrame`, its
inline-frame derivation, and mark/icon/facet helper functions. Extract the
shared facet value types and composition into a live Layout module before
deleting the allocator and mapper. Remove dormant `LaneMeasurementIdentity` /
`SurfaceLanePlan` request/Scene plumbing; the live preflight is
`preflight_fixed_lane_layout` and does not use them. Remove the unused
`lane_seed` adapter too; its stated staging condition can no longer become
true after the data-only pivot. A narrow
function-level reachability assertion should name the retired entry points;
generic call-graph analysis is not warranted by this issue and risks false
positives from dynamic dispatch. Remove any stale float-sum exception tied
only to the retired function.

Specs 38/49/50 already put membership in Project/View and finished geometry
in Layout. This decision leaves the Scene/adapter boundary and public bytes
unchanged. The test must render the actual 02/11/12 closures, inspect each
completed Scene dependency segment against required lane/member text bounds,
and cite its real name in the release review. Historical design/review records
remain history; correct the current acceptance review's false test claim.
