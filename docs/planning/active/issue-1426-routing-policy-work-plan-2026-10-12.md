# Issue 1426 — single-policy routing performance and budget

## Baseline and design plan

READY base: `96244e3d056bc93feefb88a468c604c33e1266ec`.
Authority: [updated issue](https://github.com/tya5/chrona/issues/1426) and
[owner/reviewer decision](https://github.com/tya5/chrona/issues/1426#issuecomment-6116338205).
PR1428 currently has the earlier implementation at `a9c1769d`; its CI38192929175
passes, but that is not acceptance of the rewritten scope. No authored examples
or managed outputs may be changed. Keep one routing path and remove the rejected
declaration, shapes, one-pass phase changes and their diagnostics/tests.

Use cases: speed up unchanged rendering; allow authors an additional local
expansion ceiling with honest instance/pass exhaustion evidence. Schema and
resource model: only optional positive-integer Layout `searchBudget`; no search
enum, resource kind or Scene schema. Omission preserves all current output.

## Selected design and whole-architecture review

Specification50 §3.3 owns the single-policy/budget contract. Preserve the exact
bound, histories, pair quotas/order/ranking, entry completion and all existing
label rehearsals/recovery. Layout owns counters and completed geometry; Scene
projects typed facts, and its independent contrast observer retains exact
validation/findings while using the runtime ABC and prepared immutable candidates.
Coordinators preserve executed-pass budget facts, including rejected trials.
Until1427 lands, absent accepted routes keep current suppression/fallback.
No abandoned `search` field remains in authored schemas, normalized manifests,
frozen vocabulary or CLI info. There is no default-flip migration in1426.

Review: consistent with Spec33 phase/ownership, Spec50 bounded search versus
impossibility, Spec56 additive budget normalization and Spec66 producer evidence.
The earlier finite-quota counterexample justifies retaining the exact algorithm;
it does not authorize changing closed scope. 1427 no longer reuses removed shapes;
its View overflow/mode authority and always-drawn edge cases need its own design.

Measurement audit: previous 53.933/53.795-second results were obtained with
first-fit active. They do NOT prove the retained policy meets60 seconds. Remeasure
all three inputs after removal; report any gap rather than relabel the evidence.
Previous 46/46 counterfactual best Scene/SVG identity is a useful control; replace
it with real unchanged-input materializers without a normalization override.

## Literal acceptance

| Criterion copied from the updated issue | Required evidence |
| --- | --- |
| Every example Scene and SVG is byte-identical without `searchBudget`. | All46 actual public materializers, original declarations and full bytes; current-head CI. |
| A test: a relation that reaches its budget is reported with its id and pass, and handled by suppression (later by #1427). | Synthetic blocked relation, actual suppression and typed Scene/CLI receipt; retain best accepted candidates on budget stop. |
| The three trial inputs are re-measured. The 1000/228 CPU time is reported against the 60 s budget. | 19/10,200/46,1000/228; user+system CPU/RSS and repeat hashes under the retained policy. |
| Do not edit `examples/**`. | Authored diff clean; bot/disposable outputs only. |

## Implementation plan

Finalized against the published design correction `17bef2a7`. Product changes
start only after this plan is published. Removal and budget retention are one
coherent code slice in PR1428; the batch evidence follows on the same branch.

1. Remove rejected policy: schema/vocabulary/frozen definition and policy site;
   engine/manifest flag; relation_shapes module and shape/policy-only tests;
   selector shape branches, surface summary and phase/entry special cases.
   Restore related existing oracles/CLI golden from current main, while retaining
   the independent annotation zero-leg regression fix and tests.
2. Keep explicit budget: iterator accounting, immutable selection receipts,
   schema normalization and canonical omission; typed hit info without a search
   discriminator; all-pass coordinator facts. Replace policy tests with budget
   declaration/inheritance/invalid/suppression tests. Focused routing, marker,
   annotation, pass and CLI tests; schema-equivalence and ownership guards.
3. Simplify the batch CLI to actual unchanged-input materializers, no policy
   override or two-policy delta table. Verify all46 Scene/SVG pairs and remeasure
   the three trials. If retained-policy cost misses60, review measured cost and
   only behavior-preserving corrections within this scope; publish any newly
   required contract/ownership decision before code.
4. Publish one coherent correction to the same PR after design and plan publication.
   Inspect current-head CI/artifact and literal acceptance; release on the READY
   tip and close only after exact-main three-OS checks containing the review.

The selected design/architecture correction is published; publish this finalized
implementation plan before product changes. No new PR,
force push, authored example repair or hidden compatibility routing path.
