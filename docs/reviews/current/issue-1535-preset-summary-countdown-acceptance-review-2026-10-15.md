# Issue 1535 acceptance review

Implementation: `4643606d0`; public base: `d2992523a`.
[Approved design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1535#issuecomment-6189469928).
Release status: [PR 1547](https://github.com/tya5/chrona/pull/1547), latest-head PR
and exact-main three-OS gates pending; issue remains open.

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| A summaryProfile member in preset-library-v0.2 and presentation-preset-v0.1; generic binding without a project value or diagnostic for an unresolved slot | met | Optional members, exact Summary copy, explicit override, selected-project fact, dormant connections; focused copy/closure and derived-figure tests. |
| render --preset titlecard on halcyon-1 and on chrona-roadmap draws a number in the countdown frame, viewed as PNG | met | Public CLI commands below; both PNGs inspected: **91 DAYS** and **65 DAYS**, title **完了まで**. |
| Every other preset is byte-identical | met | Batched public CLI SVG comparison against the base: all other 14 preset ids × both projects, **28/28 identical**. CI artifact 11964367812 also retains all 50 public SVGs and 50 Scenes byte-identically; only diagnostic/coverage inventories change. No examples or generated evidence edited. |
| Synthetic tests cover the new fact, with and without selected items | met | Core/projection tests cover span/point maximum, ghost/scenario/actual exclusion, duplicate identities and absent dates; integration covers missing as-of, required fixed slot omission, strict explicit figures and invalid references. |
| The schema equivalence result is in the PR | met | L1 passes: two additive preset schemas, four declared View fact-union expansions. [CI conformance](https://github.com/tya5/chrona/actions/runs/38719293306/job/116370626423) passes L2/L3: 465 mapped documents, 739 probes, 20.6s within 60s. The local 94.2s runtime failure was host-dependent, not waived. |

```sh
.venv/bin/chrona render examples/halcyon-1/project.yaml --preset titlecard --actual examples/halcyon-1/actual.yaml --format png --output /tmp/halcyon-titlecard.png
.venv/bin/chrona render examples/chrona-roadmap/project.yaml --preset titlecard --actual examples/chrona-roadmap/actual.yaml --format png --output /tmp/roadmap-titlecard.png
.venv/bin/python -m tools.schema_equivalence --base-rev origin/main
```

Architecture review: View gathers selection and supplies neutral dates; Core
performs arithmetic; Layout prunes typed semantic absence and remaps resolved
node distance paths without changing authored identity. Scene/adapters do not
infer dates or missing content. No project/node-name branches were introduced.
The frozen common fact digest update uses Spec56 §7's single-consumer exception:
its only external consumer is the live View v0.28 changed in this PR.

Focused results: 122 render-usecase/Core/projection/content/Layout tests;
137 schema-part/connection/content tests; 66 derived-figure tests, plus the
new ordinary-heading regression (6 selected tests passed). Full pytest,
conformance, wheel/smoke and public materializers remain CI release gates.
CI review finding: the two new Summary id reference sites must be counted in
the schema identity inventory. Its test census now includes both, preserving
the existing Summary opaque-id grammar; no product semantics or test guard
was relaxed. This addresses the sole failing test in run38719293306 (4005 other
tests passed in that shard); derived-ready failed consequentially.
