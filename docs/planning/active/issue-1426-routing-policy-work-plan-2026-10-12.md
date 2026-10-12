# Issue 1426 — declared routing policy

## Baseline and design plan

Published base: READY `133332e2833ede4423e775c1dec789db91c2d5cb`.
Authority: [issue 1426](https://github.com/tya5/chrona/issues/1426), including
its revised scope and algorithm review; Specification 50 and the Layout schema.
Stage: shape/phase and policy wiring implemented and locally verified on WIP.
Explicit budget selection/wiring is implemented; approximate-search
disposition and public acceptance remain incomplete.

Verified: `select_relation_route` ranks all pairs when given a rank callback;
the search uses a finite per-pair quota and path-history state. Label recovery
is conditional, not an unconditional second pass. Layout owns these decisions;
Scene and adapters must receive completed routes, not choose policy.
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

- Implement the explicit per-instance/per-pass budget selected by reviewer
  [6115714566](https://github.com/tya5/chrona/issues/1426#issuecomment-6115714566).
  Specification 50 owns the accounting and typed stop contract; zero, boolean,
  null and non-integer declarations are invalid, not unlimited budgets.
- Preserve `best` candidate/quota/order semantics. Cheaper heuristics and
  node/direction dominance require equivalence evidence: different visited
  histories can have different self-overlap-safe continuations. The proposed
  disposition is pending the reviewer response on the issue.
- Agree a schema-ready preparatory boundary or joint publication so reviewer
  `search: best` declarations precede the default flip. Coordinate with 1427's
  later `unroutable: suppress` declaration without implementing its modes here.

Existing #1420 visibility/incremental preparation is shared; endpoint assembly
and reverse-bound work remain distinct. No typing-protocol hot checks were
found in the inspected modules. Verify actual costs before further optimization.

Measured next hot path: a 200/46 profile spends 19.42 of 30.44 profiled seconds
in completed-Scene contrast inspection, versus 1.82 s routing; 5,874,640 typing
alias checks occur. The local Python implementation delegates those ordinary
checks to the runtime Mapping ABC. Use that ABC without changing contrast rules
or skipping inspection. Exact findings/payload comparisons cover all public
manifest-declared Scenes and synthetic dict/UserDict/proxy inputs; the affected
contrast/ground/pattern suite has 265 PASS (13.72 s). This internal hot-path
slice was planned on issue comment 6115452760; it changes no public contract.
The subsequent internal plan (6115533053) prepares stable per-surface primitive
candidate categories and first-id lookup once, retaining original indices,
all exact query-time predicates and failure order. No global cache or input
mutation. Cached-versus-uncached full public findings/payloads, malformed ink,
paint-order ties, duplicate ids, nested mapping types and preparation counters
pass: 272 focused tests, 10.74 s; Scene delivery/import/reachability checks pass.
The measured CLI results below replace the initial wiring measurements.

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

Foundation and policy wiring are implemented. Focused routing/terminal/profile,
shared-schema and actual Scene/SVG/info batch: 412 PASS, 28.56 s. Ranked-route
oracles explicitly use best, retaining every prior assertion; 18 round-terminal
combinations additionally cover both policies. No-graph and actual fallback
controls, foreign-host collisions, terminal refusal and self-overlap rejection
remain covered. S0/L2/L3, schema/reference, inward import (11/37), reachability
(236, none orphaned), Scene delivery and float/diff guards pass. Four already
merged #1343 schema deltas were retired by the equivalence tool. Vocabulary
report is stale by the one new declared site; CI regenerates it, not a manual
patch. No authored examples or managed outputs change; full pytest is CI-owned.

Current three-input measurements (CPU=user+system, not wall time):

| Objects/relations | CPU seconds, runs 1/2 | Peak RSS MiB, runs 1/2 | Shape/search counts |
| --- | --- | --- | --- |
| 19/10, public `routing_revision/project-v1.yaml` | 0.91 / 1.08 | 73.0 / 76.6 | 9 / 1 |
| 200/46, `routing_scale_project(200)` | 4.033 / 4.164 | 100.5 / 100.3 | 43 / 3 |
| 1000/228, `routing_scale_project(1000)` | 53.388 / 53.324 | 197.5 / 196.7 | 210 / 18 |

All six renders succeed; Scene/SVG hashes match within each pair and the prior
wiring outputs. Both 1000 runs meet 60 s versus the published approximately
3,170 s baseline. This is not whole-issue acceptance: explicit budget/search
scope, public-output review, target migration and CI release remain required.

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
Approximate-search disposition remains unresolved. The subsequent budget
slice adds no ignored public declaration.

## Budget design and whole-architecture review

Selected authority: Specification 50 §3.3 and reviewer decision A. The optional
ceiling supplements the legacy quotas rather than changing absent-budget best
output. Actual expansion receipts belong to the Layout iterator and selection;
fresh counters belong to resolved instances, not logical Project relations,
port pairs or the whole render. Pass coordinators retain all typed hit facts,
including rejected rehearsals, without leaking rejected geometry into Scene.
The existing deterministic progress-pass identity distinguishes those facts.

Review: consistent with Spec 33's Layout ownership and phase model, Spec 50's
bounded-search/non-impossibility distinction, Spec 56's additive optional
schema/normalization rules, and #1300's locality. #1427 consumes an absent route
through its separate mode; this slice does not implement modes, claim exhaustive
search or waive current suppression. Scene/CLI project facts only. Migration:
explicit authors may intentionally select a different route by cutting search
short; omission preserves declared best behavior. No new resource, Scene
schema, adapter geometry, cache-dependent allowance or project-specific rule.

### Budget implementation plan

1. Iterator/selection foundation: `route_search` owns an instance-local mutable
   expansion counter; `routing` creates one only for an explicit ceiling and
   shares it across pairs. Preserve existing quotas/order when absent, charge
   seeds and processed non-stale states before work, retain accepted candidates
   on exhaustion, and return immutable count/stop receipts. Tests cover early
   iterator close, exact boundaries, graph memo reuse, multiple pairs, accepted
   best preservation, shape-only zero charge and invalid internal inputs.
   Publish this independently testable internal slice without an ignored schema
   member or runtime declaration.
2. Profile/diagnostic wiring: additive positive-integer schema member, engine
   normalization and manifest canonicalization (omit when absent); pass ceiling
   to selection. Add typed budget hit facts with deterministic existing pass
   names; lane and route/label coordinators preserve all executed trial facts.
   Scene and CLI transport typed facts only. Test inheritance/replacement,
   invalid authored values, both policies, all pass outcomes and diagnostic
   byte identity when absent; run schema-equivalence and ownership checks.
3. Combine with the issue's public batch, repeat hashes, reviewer target
   migration and current-head/exact-main CI gates. No issue closure or default
   flip from foundation tests alone. Approximate-search disposition is separate.

Foundation implemented: expansion counters are charged before seed/frontier
processing, shared across pairs and frozen into selection receipts. Exhaustion
stops pair selection without discarding a previously accepted route; shapes
charge zero. Focused iterator/selection/history/memo tests cover early close,
exact ceiling, cached graphs, rejected candidates, preserved rank winners and
nonbinding-budget legacy equality. Public profile/diagnostic wiring now carries
the positive-integer ceiling through engine/manifest to selection. Typed hits
include actual per-pass identities and reach Scene/CLI; lane and label
coordinators retain all executed trial receipts, even rejected trials. Real
lane/automatic renders cover both policies, and synthetic controls prove
rejected recovery/reservation facts survive without retaining their geometry.
Schema equivalence: S0 additive=1/equal=37, L2+L3=15.8 s, PASS.
Legacy lane-corridor tests explicitly declare best without changing their
existing assertions: their pre-name/recovery premises do not apply to the
owner-selected first-fit default. Public output/reviewer and CI gates remain.

### Wiring implementation plan

1. Add the shared vocabulary/frozen definition and optional Layout schema
   member, with finite-vocabulary policy and schema probes. Normalize it in
   `engine.solve_layout`; carry it in `LayoutManifest`, preserving best's
   legacy canonical payload. Tests: `test_relation_search_profile.py`, shared
   vocabulary/schema tests and schema-equivalence against current main.
2. Pass the policy and completed row-gap channels to `surface_routes`; carry
   actual search-use evidence from selection, and complete the selected
   entry-side back-route rule. Tests: shape selection including a later shape
   after failed search, existing entry/back-route and terminal safety tests.
3. Partition only member/delta requests after routes under first-fit in
   `surface_composer`; bypass lane rehearsals and disable lost-name recovery
   through `surface_route_label_plan`. Best keeps its old path. Test actual
   routing-call counts in synthetic lane and automatic Scene/SVG renders,
   with the pre-existing recovery tests as negative controls.
4. Produce the typed summary in Layout, hand it through `surface_completion`
   to existing Scene info projection, and add an explicit payload mapping in
   `draft_render.warning_payloads`. Tests validate count invariants, actual
   Scene diagnostic JSON and CLI/MCP severity; no adapter geometry/counting.

Publish this approved slice plan before code. Keep the combined code on the
same issue WIP; no default-flip merge or release acceptance before reviewer
migration and all remaining budget/search/public-output gates. Focused tests
and schema/ownership checks precede publication; use CI for full-suite release.

## Literal acceptance — release still pending

| Criterion copied from the issue | Required evidence |
| --- | --- |
| Under `best`, every existing example and route test is byte-identical. The reviewer declares `best` on the five approved design targets before the default changes; land that YAML first or in the same release. | Legacy-versus-best characterization, batch artifact diff and coordinated reviewer publication. |
| Under `first-fit`, list changed routes per example slide with counts: routes changed, bends ± and length ±. The reviewer accepts or rejects them in the PR. | Per-slide route delta table and explicit PR review. |
| A counter test shows that under `first-fit` a relation settled by a shape performs no graph build. | Synthetic counter test with a graph-building negative control. |
| The three trial inputs are re-measured, and the 1000/228 CPU time is reported against the 60 s budget. | Reproducible CPU/RSS measurements for verified inputs, without substituting wall time. |
| Output is byte-identical across two runs. | Scene/SVG hashes for repeat runs under the declared policy. |
| Do not edit `examples/**`; the reviewer adds `search: best` to the targets. | Authored diff and reviewer-owned migration evidence. |
