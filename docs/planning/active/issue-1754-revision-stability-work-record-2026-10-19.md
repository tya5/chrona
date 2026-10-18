# Revision stability — issue 1754

## Published baseline and scope

Design planning for the whole issue; S1 identity design completed below.
Source: [issue 1754](https://github.com/tya5/chrona/issues/1754), including its later comments, on ready main `6c3b4e4e2d4064e924a8b9703c3f31ab7a62bc39`.
Trial evidence is reference-only: [`reviewer/trial-8-inputs@bf3940dbe9af487ac6cace5458554762594f3477`](https://github.com/tya5/chrona/tree/bf3940dbe9af487ac6cace5458554762594f3477/trial-8).

Published facts: core relation identities include the declaration index;
Layout consumes previous-Scene hints only under first-fit; Spec 50 explicitly
excludes best and makes the as-of rule obstruct member names; Specs 08/46
include the cone in completed contrast grounds. These contracts must change
before code. Trial measurements are reported evidence, not yet independently
reproduced on the implementation. Duplicate declared-ID handling, best-mode
hint preference and the Theme ground opt-in remain design decisions.

Dev A owns this item. Dev B owns baseline/forecast 1755 and customisation
1756. Coordinate shared-file changes before implementation; do not alter trial
inputs or preset YAML to satisfy a general rule. Completed 1734 geometry reuse
and its safety/accounting rules remain the routing baseline.

## Literal issue rules

1. A relation with a declared, unique `id` is identified by that id alone. Without one, it is identified by its endpoints and type, with a declaration-order suffix only to separate exact duplicates.
2. Previous-Scene hints apply under every search policy: as the first candidate for `best` as well as for `first-fit`, still revalidated. Where a policy cannot use them, emit an `I_` diagnostic saying so.
3. A route whose endpoints and obstacles near it are unchanged keeps its corridor when one still validates (hint-first). Prefer a detour over crossing a mark before accepting a through-mark route.
4. The as-of line is not a label obstacle that suppresses a member label: labels may cross it, using the existing halo/chip treatment.
5. Contrast observations over a moving decoration (the as-of cone) are judged against the mark's own ground, not the cone, unless the Theme declares otherwise.

## Literal acceptance and required evidence

| # | Literal acceptance criterion | Evidence to produce |
| ---: | --- | --- |
| 1 | Synthetic: removing one relation and appending another keeps every other relation's primitive id; hints are accepted for all unchanged relations. | Canonical identity, scheduler/Model/Scene and previous-Scene synthetic tests, including anonymous/duplicate relations. |
| 2 | target-b with `--previous-scene` uses the hints (receipts show accepted hints), or reports why not. | Real render and per-instance/summary receipts under best, plus unsupported-mode diagnostic tests. |
| 3 | A synthetic slip that does not touch a relation's endpoints keeps that relation's route; no new through-mark crossing appears where a detour exists. | Completed-route geometry before/after, current validator results and an obstructed-route negative twin. |
| 4 | Re-running trial 8 with hints: the changed-primitive count of unchanged objects falls, and the table is posted on the issue. executive-light labels of unchanged tasks do not toggle with the as-of line. | Batch all five weeks/three designs, compare unhinted and hinted revisions on the same candidate, post table and inspect rendered label output. |

## Design plan and architecture review questions

Use cases are weekly redraw, inserted/removed relations, unchanged corridors
beside unrelated edits, and moving as-of decoration. Preserve intent and
source identity in core; normalize relation facts in Model; keep hint recovery,
geometry, obstruction and route validation in Layout. Scene observes completed
paint/grounds; adapters serialize without inferring placement or policy.

Review before selecting contracts:

- Define collision-free identity namespaces and duplicate occurrences, including
  duplicate declared IDs, endpoint/type normalization and public-ID migration.
  Audit scheduler critical/driving relations, lane projection and Scene matching.
- Specify hint-first acceptance under best versus ranking only fresh candidates,
  current full safety/quality validation, invalidation, receipts and budgets.
  Separate primary marks from other obstacles; never infer safety from trial data.
- Remove only the moving as-of line from member-name obstruction; retain
  deadline/other-rule contracts, route/annotation safety and existing text treatment.
- Specify precisely which contrast observations use the mark's own ground,
  how an explicit Theme declaration requests cone compositing, and transport
  through schema/Model/completed Scene without adapter-specific behavior.
- Check Specs 06/07/08/46/50/56, relevant ADRs and adjacent 1755/1756 work;
  identify intended output/diagnostic incompatibilities and old-Scene hint misses.

## Publication and implementation planning gates

1. Publish this plan before making decisions in code.
2. Complete the selected design and whole-architecture review here; update the
   living specifications. Publish before finalising implementation planning.
3. Publish implementation slices with exact owned files, focused tests,
   schema/resource migrations and affected materializer/generated-evidence gates.
   Candidate boundaries are stable identity, all-policy hint reuse, moving
   decoration handling, then integrated trial acceptance; revise after design.
4. Implement approved slices only. Run focused synthetic tests locally in this
   worktree's venv. Batch public SVG/Scene comparisons and trial renders;
   use CI for full three-OS pytest/conformance/wheel/materializer evidence.
5. Publish one literal acceptance review and release on exact main containing
   it. Close only after every row and required release job succeeds.

## S1 selected design and whole-architecture review

The canonical contract is [Spec 05 §7](../../specification/05-project-format.md#7-relations).
Core computes all identities together from the normalized relation list;
consumers receive the resulting immutable ordered tuple and never recompute an
identity after filtering. Unique declared IDs use an author-ID namespace;
anonymous, empty-ID and repeated-ID relations use an endpoint/type namespace.
Only indistinguishable fallback duplicates need a local occurrence suffix.
UTF-8 component escaping makes both namespaces collision-free. No new Project
syntax or schema version is needed. The old scalar index-based helper is
removed rather than retained as a contradictory compatibility path.

Architecture review: Spec 02 semantic identity, Spec 05 normalized relations,
Spec 57 driving/critical relations, Spec 06 projection and Spec 08 stable Scene
identity remain consistent when every consumer shares the core tuple. Spec 09
and ADR-0004 keep format/semantic ownership separate. ADR-0031 and Spec 50 keep
geometry and hint validation in Layout; this slice does not select a route or
change a schedule. Scene and adapters retain opaque source IDs and completed
primitives. No adapter interprets the new spelling. Old Scene hints fail closed
on an exact identity miss, as required by the existing previous-Scene contract.
No trial/preset-specific rule, declaration uniqueness error, or migration alias
is introduced. Dependency-network ordering may change where it used the old
derived ID; disclose generated output changes rather than preserving unstable
order. Exact duplicate removal cannot promise per-copy identity; unique IDs
are the explicit extension point. Removing a repeated declared ID can make its
survivor unique and therefore move it from fallback to author-ID identity;
uniqueness is itself changed input under rule 1, not an unrelated edit. The
synthetic removal criterion exercises relations whose identity inputs stay
unchanged; no cross-revision alias or stateful identity registry is introduced.
No unresolved S1 contract remains.

S1 is independently testable and does not claim any
full issue acceptance row met until integrated hints and trial evidence exist.

## S2 selected design and whole-architecture review

[Spec 50 §3.3](../../specification/50-constraint-driven-gantt-surface-quality.md)
owns the revised all-policy hint-first contract. Issue rule 3 settles the
ranking question: a currently valid prior corridor wins, even if fresh best
search could rank another route higher. Without a valid hint, ordinary ranked
best behavior is unchanged. No trusted/forced-route API or persisted geometry
is added. Reuse the existing candidate preparation, admitted port pairs,
completed terminal/mark/obstacle/self-overlap/quality validators, and expansion
accounting. Hints are normal-domain proposals only. A post-selection optional
back-route improvement must not replace an accepted hint.

Architecture review: core identity remains S1-owned; immutable prior Scene
ingress and materializer integrity stay in the application/closure layer.
Layout alone reconstructs/reanchors/validates geometry and emits existing
typed hint receipts and summary under both policies. Explicit overlap/stub
report why they bypass hint selection. Scene emits completed paths and adapters
remain serializers (ADR-0031, Specs 08/09/50). No schema, Scene mutation,
budget increase, or quality exemption is needed. Existing staged detour-before-
mark relaxation remains authoritative; trial 8's Observability stack is a
primary work mark, not a header. A newly invalid hint must fall through to
safe ordinary routing, not become reusable in a relaxed domain. Bounded search
is not mathematical feasibility proof; tests must provide a known legal
detour and verify actual completed geometry, not merely a warning count.
No unresolved S2 contract remains.

## S3 selected design and whole-architecture review

Spec 50 owns the as-of-line exception for member names. Apply one exact-ID
query exclusion to their placement snapshot, before both candidate contact
generation and collision checks. Use the same path for final names, required
names, reserve-only names and route-blocked reservation probes. Do not remove
the shared `as-of` obstacle, omit the `rule` class, or weaken generic overlap
checks. Deadline rules, the separate as-of label/chip, required text, marks,
routes and annotations retain their existing contracts and treatment.

Architecture review: Layout retains sole geometry and obstacle-policy
ownership (ADR-0031/Spec 50). A generic exact-ID exclusion on the existing
independent obstacle-query snapshot avoids a second label pipeline. Accepted
labels still register in the original inventory; exclusions do not leak to
later annotations or routes. Existing geometry overrides remain applicable;
prepared-query sharing/memo scopes may be retained only for exact unaffected
content (1734). Scene/paint treatment and adapters are unchanged; no new
schema, Theme role, threshold or project-specific exception is needed. Cone
contrast is a separate S4 rule, not a reason to alter this placement boundary.
No unresolved S3 contract remains.

## S4 selected design and whole-architecture review

Specs [07](../../specification/07-style-and-theme.md#9-boundary-to-scene-and-rendering),
[08](../../specification/08-scene-and-rendering.md) and
[46](../../specification/46-completed-scene-paint.md) own the cone-ground rule.
One optional boolean author opt-in becomes one completed cone fact. A runtime-
only evaluator switch was rejected: Scene-only corpus analysis could not then
honour the Theme choice. A new extensible ground-policy language or additional
enum is unnecessary for this binary choice. Put metadata on the primitive,
not gradient paint, so adapter paint identities cannot change merely because
an observation policy changes. Do not make severity imply ground membership.

Architecture review: Theme resolution validates author intent; Scene paint
completion projects that intent onto the emitted cone. The shared Scene
observer reads only completed facts and selects the cone set once per
classified mark observation, including encoded fills, patterns and multipart
marks. Recursive grounds use that same selected set. Text retains all physical
cones. Physical surface-treatment samples retain their separate actual-paint
contract. Layout geometry, Scene geometry and all adapters are unchanged.
The optional Theme/Scene boolean is an in-place input widening (Spec 56);
the default mark-ground interpretation is an intentional normative correction,
not a claim of behavioral compatibility. Older v0.7 Scenes without metadata
adopt it; v0.6 admission is unchanged. Revalidate default and opt-in severities,
ground IDs and exception disposition. No project/preset branch or resource
migration is required; updated generated diagnostics will be reviewed as a
batch. Independent review supports Scene-carried policy and this separation
from physical paint. No unresolved S4 contract remains.

## S1 implementation plan

| Slice | Owners/files | Acceptance and focused evidence | Publication |
| --- | --- | --- | --- |
| Canonical closure | `core/relation_identity.py`; scheduler driving/critical consumers; Model lane/network projection; review `v05_content.py` | One batch helper, no old index helper/call site. Unique IDs and fallback endpoints/types remain stable across unrelated insertion/removal/reorder; duplicates and delimiter/Unicode collisions covered. Scheduling dates/critical membership and projection roles remain correct. | One implementation commit with synthetic consumer tests; no example/schema edits. |
| Consumer migration | Core, scheduler, Model/Scene and previous-Scene tests that pin the old derived spelling | Replace only intended derived-ID expectations. Keep authored IDs/coordinates/diagnostics unchanged unless directly required by the contract. Test an older Scene produces explicit hint misses rather than positional reassignment. | Same S1 PR; no compatibility shim. |
| S1 gate | Core identity tests; scheduler tests; projection rows/network and review content tests; previous-Scene/revision integration tests | Focused suites locally. CI three Ubuntu shards/conformance/MCP/newest-Python reproduction. Batch the official before/after snapshot: count renamed primitives separately from moved geometry, inspect any actual geometry/diagnostic changes. No manual generated-file edit. | Publish after pre-code design and this plan; disclose identity migration in PR. Keep issue open for S2 and integrated acceptance. |

Run schema equivalence only if implementation reveals a real schema change;
none is planned for S1. Full three-OS/wheel release evidence remains required
on the exact main containing the final issue acceptance review. If a consumer
cannot use the shared identity without a new semantic rule, return to design
before changing that rule. Do not expand S1 into hint/routing or Theme policy.

## S2 implementation plan

- Owners: `layout/routing.py` validates preferred routes under both policies;
  `surface_routes.py` proposes/records hints under both, protects accepted hints
  from optional back-route ranking, and retains explicit unusable receipts.
  Update the CLI-reference description and link it from `update-a-plan.md`.
- Tests: replace the two obsolete best-ignores-hints tests in
  `test_preferred_relation_route.py` and `usecases/test_previous_scene.py`;
  exercise accepted, rejected, unadmitted and obstacle-invalidated hints under
  both policies, including a better-ranked fresh candidate, no search on a hit,
  honest expansion receipts, and overlap/stub unusable diagnostics. Extend the
  revision integration synthetic with an unrelated slip and a known mark-safe
  detour. Keep recovery/shape/quality/critical tests as regression controls.
- Publication: a separate reviewed implementation commit in the issue branch;
  batch S1/S2 in the issue PR after the design publication, rather than spending
  another main-ready cycle per helper. CI and one official public snapshot cover
  the combined slice; disclose ID/geometry/diagnostic changes separately.
- Acceptance: synthetic retained primitive IDs and accepted hints under best,
  an invalid hint falls through without a mark crossing, existing unsupported
  modes explain themselves, and no-hint selection is unchanged by S2 itself.
  Real target-b and five-week trial evidence remain the integrated issue gate.

## S3 implementation plan

- Extend `SurfaceObstacleIndex.copy` with an exact `excluded_ids` query option.
  Keep the original inventory intact; detach only prepared selections whose
  exact contents change. Combine exclusions with existing paint-footprint
  overrides without reusing a geometry-dependent memo under different content.
- In `surface_member_labels.py`, exclude only `as-of` for `memberLabel` query
  snapshots. Both contact generation and collision checks already consume that
  snapshot; final/reserve/recovery paths share this owner. Keep all registrations
  on the original index. No generic label-ladder or adapter policy is added.
- Focused tests: `test_obstacles.py` for independent snapshots, exclusions plus
  overrides, exact selections and absent exclusions; `test_member_label_required_phase.py`
  for final/reserved names crossing as-of while deadline rules still block;
  `test_member_label_route_obstruction.py` for the same route-blocked probe.
  Retain as-of-label and annotation-asof tests as negative controls. Run routing
  working-set regressions because the copy helper shares immutable query data.
- Publish a coherent implementation/test commit in the same issue PR; use one
  CI/public snapshot and final trial batch for the combined slices. No schema,
  example or manual generated-output changes. A label/chip or other obstruction
  remains truthful; this is not a general guarantee that all names always fit.

## Current implementation evidence

S1 is implemented locally; publication/public-output review and CI are pending.
The batch helper replaces every runtime scalar caller. Scheduler passes the
same identified tuple to its critical-path closure. Focused batches passed:
171 scheduler/identity/lane/network/Model tests; 150 review-content, hosted-point,
critical-role, previous-Scene and revision-regression tests; one new integrated
remove/append test with accepted retained hints and explicit old-ID misses.
After threading the Scheduler tuple, its identity/scheduler subset passed
again (15 tests). Eight migrated integration modules compile and collect
(183 cases); their expensive corpus checks remain assigned to CI. Independent
S1 review found no remaining identity/ownership blocker; the uniqueness-change
limitation above is explicit. No schema, preset or generated output is edited.
S2 now validates hints under both policies and preserves an accepted hint
before optional back-route ranking. Focused routing/hint/recovery/revision
batch: 52 passed; previous-Scene and update-guide batch: 22 passed. These
include best accepting retained IDs, failed hints falling through, unchanged
old-ID miss behavior, and explicit overlap/stub unusable receipts. A default
plot-name/stub collision reproduced on public `1de259e69` is independently
tracked in [1763](https://github.com/tya5/chrona/issues/1763); the receipt test
uses a valid table-label View without changing product behavior for that bug.
The real three-row slip/detour synthetic passes under both policies (2 cases):
an irrelevant slip keeps the validated corridor; moving a primary mark across
it invalidates the hint and accepts a mark-clear detour in NORMAL, before mark
relaxation. Endpoint geometry is unchanged and actual paths are compared.

S3 exact-ID query exclusions and all placement paths are implemented. The
obstacle/member-name/as-of-label/route-memo/annotation negative-control batch
passes (77 cases). The original inventory and other rule obstacles remain
intact. Public snapshot/CI and full trial-8 acceptance are still pending;
S4 cone-ground design and implementation remain incomplete.
