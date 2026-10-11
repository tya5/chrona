# Issue 1426 — declared routing policy

## Baseline and design plan

Published base: READY `133332e2833ede4423e775c1dec789db91c2d5cb`.
Authority: [issue 1426](https://github.com/tya5/chrona/issues/1426), including
its revised scope and algorithm review; Specification 50 and the Layout schema.
Stage: first-fit shape/phase design selected; budget and approximate-search
design slices and the final implementation plan are not complete.

Verified: `select_relation_route` ranks all pairs when given a rank callback;
the search uses a finite per-pair quota and path-history state. Label recovery
is conditional, not an unconditional second pass. Layout owns these decisions;
Scene and adapters must receive completed routes, not choose policy.
Published timing evidence is approximately 3,170 CPU-seconds for 1000/228;
new-policy timings and output changes remain unverified.

Baseline focused validation: 69 tests pass in 2.31 s (visibility preparation,
graph memo, path-history/intersection equivalence, routing placement, label
recovery and diagnostic details), in this worktree's Python 3.13 venv.
Additional characterization/budget/selection batch: 25 pass in 1.75 s.
The [finite-quota counterexample](../../../tests/unit/chrona/presentation/layout/test_routing_policy_characterization.py)
finds three candidates with the exact reverse bound and zero with an admissible
geometric bound under the same 32-expansion quota. Ranked selection succeeds
before and fails after that bound-only change. Applying that optimization to
`best` therefore contradicts its unchanged-output criterion; this is measured
evidence, not an assumed risk. Selected-design disposition still needs agreement.

Use case: authors choose inexpensive deterministic routing or the existing
ranked routing, without a project-size threshold. The default change is an
intentional migration, coordinated with reviewer-owned target declarations.
No developer changes to `examples/**` or managed artifacts are permitted.

### Decisions to close before implementation

- Define exact port-pair order and finite straight/L/Z/U shape order, including
  ties, row-gap/channel derivation, and existing terminal acceptance.
- Define expansion accounting across pairs and label recovery, exhaustion
  diagnostics, zero/invalid budgets, and counters without claiming that a
  bounded search proves geometric impossibility.
- Preserve `best` candidate/quota/order semantics. Cheaper heuristics and
  node/direction dominance require equivalence evidence: different visited
  histories can have different self-overlap-safe continuations. The proposed
  disposition is pending the reviewer response on the issue.
- Reconcile Specifications 50/56, normalization, placement identity and
  diagnostic ownership. Locate actual hot-path costs rather than assuming
  every algorithm-review observation still describes current code.
- Agree a schema-ready preparatory boundary or joint publication so reviewer
  `search: best` declarations precede the default flip. Coordinate with 1427's
  later `unroutable: suppress` declaration without implementing its modes here.

### Whole-architecture findings

- Specification 33 retains required lane labels before routes and one optional
  lost-name recovery. Specification 50 also retains up to three lane-reservation
  routing rehearsals. Merely skipping `surface_route_label_plan` recovery does
  **not** satisfy the new one-pass contract. The selected first-fit phase order
  must bypass lane rehearsals and place lane member names/deltas after routes,
  while retaining already completed axis/period/other required text as obstacles.
  Keep both legacy label/rehearsal rules under `best`; update both specifications
  together before code. Data-only lane membership, label association/reach and
  window admission must not change.
- Specification 33 defines top-level `relationRouting` replacement in derived
  profiles. Preserve that rule; do not merge individual routing members or
  silently inherit a discarded base policy. Existing schema-required limits
  remain required when the object is authored.
- Specification 50 already preserves exact endpoint-independent base visibility
  and incremental obstacle additions (#1420); current tests prove ordered graph
  and reverse-heuristic equality. This is existing shared preparation, not a new
  unimplemented capability. Endpoint graph assembly and reverse Dijkstra remain
  distinct costs. No runtime typing-protocol checks were found in the inspected
  search/routing/obstacle modules; do not claim removing nonexistent work.
- Specifications 37/49 preserve completed Layout geometry and immutable semantic
  inputs; neither Scene nor a usecase should own the new shape/port policy.
  Specification 56 governs optional in-place schema additions and truthful
  ingress failures. Specification 66 transports producer-owned diagnostic facts.
- Shape success must reuse full corridor/terminal preparation and final safety,
  bounds and quality validation, not only a raw segment collision check. Existing
  node-sharing diagnostics remain necessary when first-fit stops before ranking.
  Budget exhaustion remains a search disposition, never a no-safe-route proof.

### Design and evidence order

1. Characterize existing ranked routing, policy normalization and conditional
   label recovery; complete the selected normative design and whole-architecture
   review. Owners: Layout engine/model, routing/search, surface routes and label
   plan; schema/vocabulary/default gates and Specification 50.
2. Publish the implementation plan with independent schema/migration and
   policy/efficiency boundaries, affected files and focused acceptance tests.
3. Implement only approved contracts; batch disposable public materialization,
   route deltas and the three trial measurements. Retain synthetic PR-path
   tests for every corpus rule. Use CI for the full three-OS release gate.

## Selected first-fit slice and architecture review

Specifications [50](../../specification/50-constraint-driven-gantt-surface-quality.md#33-relations)
and [33](../../specification/33-intent-oriented-layout.md) now state the exact
port/shape order, channel derivation and one-pass phase order as
implementation-pending contracts. The shape proposal is bounded to seven raw
paths per pair; it owns no best-route or geometric-completeness promise.
Geometry and acceptance stay in Layout; source ports remain semantic, existing
connected-host exemptions stay scoped and Scene/adapters project only completed
results. Required text is not globally deferred: only member-name/delta
placement moves. The natural row/mark allocation and data-owned lane partition
remain unchanged. There is no new resource kind or previous-Scene input.

Architecture decision for this independent slice: accept the owner-selected
first-fit output change, retaining exact best behavior. Risks to verify before
acceptance: terminal preparation after raw collision admission, row-contact
routes, mirrored/point/compound endpoints, lane-name suppression, windows and
residual node sharing. Other scope items remain planned, not waived or deferred
out of this issue. No product implementation is authorized by an unresolved
budget or approximate-search decision.

## Implementation plan — shape-selection foundation

The first independently testable slice implements the selected shape/port
contract without switching runtime defaults or adding an ignored public
declaration. Design-stage conformance passes all 35 checks; L2+L3 is 16.3 s.

| Slice | Owners/files | Verification and publication |
| --- | --- | --- |
| Shape-selection foundation | Pure Layout `relation_shapes`; `routing.select_relation_route` explicit internal first-fit option, retaining the legacy default and shared full-route validation. No Scene, profile/schema, resource or generated-output change. | Synthetic order/dedup/bounds/port tests; collision/terminal/quality/self-overlap controls; shape-settled no-graph counter; existing ranked-selection and finite-quota characterization. Publish tested WIP, not a runtime-default or whole-issue release. |
| Policy wiring and one-pass composition | Schema/shared vocabulary; Layout engine/manifest, surface routes/composer and lane/label coordinators; Specifications 33/50. | Finalize counters/normalization before code; in-place schema deltas, absent/explicit policies, derived replacement, lane/automatic one-pass counters, unchanged best projection. Reviewer target migration precedes the default flip. |
| Budget and fallback efficiency | Layout search and selection accounting. | Close remaining budget/equivalence decisions and publish their normative design before planning/code; retain all issue scope, never silently drop best optimizations or substitute connectivity for byte identity. |
| Public acceptance/release | Disposable materializer outputs, benchmark tool and literal review. | Batch all best/default comparisons and per-slide route/bend/length changes; three verified trial inputs and repeat-run Scene/SVG hashes; reviewer acceptance; current-head CI and exact-main three-OS release. |

Shape-foundation acceptance is internal behavior only: existing callers and
their candidate/quota/rank behavior remain unchanged. New selection still
passes completed semantic corridors through the existing terminal preparation,
full-route safety and measured quality gates before returning a route.

Foundation implemented and locally reviewed: explicit internal first-fit
selects finite shape proposals through the existing completion function, with
an immutable shape-settled fact. Public schema/default wiring has not started.
Focused shape/annotation-diagnostic/routing/search/label batch: 119 pass in
2.85 s; inward imports, module reachability (236, none orphaned), float
accumulation and diff checks pass. The no-graph test forbids both graph assembly
and search; a quality-rejected negative control proves actual fallback graph
work. Terminal refusal, foreign-host text collision and prepared self-overlap
remain rejection controls. A malformed new fixture initially named an
unregistered host; the fixture now registers it and the exemption validator
remains unchanged. No authored examples or managed outputs change.

## Policy-wiring design review

Specification 50 closes schema normalization, derived-member replacement,
entry-side back-route order and the exact typed info summary. Layout Manifest
retains the effective policy; its legacy `best` canonical payload omits the
new member. The summary counts actual selection calls, not Scene paths or
logical Project relations, and separates no-search shape completion from any
fallback search, including a later shape winner. Existing typed info transport
requires an explicit CLI projection; diagnostic strings alone would be silently
absent from that channel. Add no paint or Scene-schema fields. Profile wiring
is additive in place; the owner-selected absent default intentionally changes
routing and label phase order, while declared best preserves old behavior.
Review against Spec 33 inheritance/phase authority, Spec 50 safety, Spec 56
vocabulary/normalization and Spec 66 producer-owned evidence is consistent.
Budget and approximate-search contracts remain unresolved; no ignored public
budget member is added by this slice.

## Literal acceptance (all currently not met for the new policy)

| Criterion copied from the issue | Required evidence |
| --- | --- |
| Under `best`, every existing example and route test is byte-identical. The reviewer declares `best` on the five approved design targets before the default changes; land that YAML first or in the same release. | Legacy-versus-best characterization, batch artifact diff and coordinated reviewer publication. |
| Under `first-fit`, list changed routes per example slide with counts: routes changed, bends ± and length ±. The reviewer accepts or rejects them in the PR. | Per-slide route delta table and explicit PR review. |
| A counter test shows that under `first-fit` a relation settled by a shape performs no graph build. | Synthetic counter test with a graph-building negative control. |
| The three trial inputs are re-measured, and the 1000/228 CPU time is reported against the 60 s budget. | Reproducible CPU/RSS measurements for verified inputs, without substituting wall time. |
| Output is byte-identical across two runs. | Scene/SVG hashes for repeat runs under the declared policy. |
| Do not edit `examples/**`; the reviewer adds `search: best` to the targets. | Authored diff and reviewer-owned migration evidence. |
