<!-- chrona:literal-acceptance/v1 -->

# Issue 1430 — default relation routing

Implementation and rendered acceptance are verified. Release remains pending
exact-main three-OS CI containing this review; the issue remains open.

## Literal issue acceptance

### Issue #1430

- Source: [Issue #1430](https://github.com/tya5/chrona/issues/1430)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Under `search: best`, every example is byte-identical. | met | [Corrected public controls](https://github.com/tya5/chrona/issues/1430#issuecomment-6121188747): all 46 full Scene/SVG pairs match; protected five also match under actual default. | — |
| 2 | Under the default, report per slide the routes changed, bends ± and length ±. Add a reviewer side-by-side note for at least the three most-changed slides. The reviewer accepts or rejects in the PR. | met | [Per-slide table](https://github.com/tya5/chrona/issues/1430#issuecomment-6121188747); [reviewer accepts the three largest geometry deltas and authorizes landing after rescue](https://github.com/tya5/chrona/pull/1435#issuecomment-6121714806). Rescue changes only roadmap and satisfies that condition. | — |
| 3 | A counter test: a relation settled by a shape performs no graph build. | met | [Shape counter and negative control](../../../tests/unit/chrona/presentation/layout/test_relation_shapes.py), `test_shape_settled_relation_never_builds_a_graph_or_invokes_search`; current-head CI below passes. | — |
| 4 | Re-measure the three trial inputs under the default; the 1000/228 CPU time is reported against 60 s. | met | [Six real CLI measurements](https://github.com/tya5/chrona/pull/1435#issuecomment-6122032807): 19/10 1.102/1.130 s; 200/46 5.710/5.647 s; 1000/228 121.285/122.200 s, 2.02–2.04×60 s. The M2 performance target is **not met**; reporting it is this criterion. | — |
| 5 | Byte-identical across two runs. | met | [Repeated Scene/SVG hashes](https://github.com/tya5/chrona/pull/1435#issuecomment-6122032807), all three sizes; [reproducer](../../../tests/support/routing_scale_benchmark.py). | — |
| 6 | Do not edit `examples/**`. | met | [PR #1435](https://github.com/tya5/chrona/pull/1435): no authored examples or generated outputs. Reviewer protection PR1433 is inherited unchanged. | — |

## Programme-level criteria (optional)

- Reviewer rescue requirement: all 46 slides have `Removed = 0`, including
  `m0-gate → presets`; [current delta evidence](https://github.com/tya5/chrona/issues/1430#issuecomment-6121188747).
  [Real cheap-failure/exact-success regression](../../../tests/unit/chrona/presentation/layout/test_routing_policy_characterization.py)
  and shared-budget/order/fast-success controls pass.
- Implementation [PR1435](https://github.com/tya5/chrona/pull/1435) merged at
  `a320a14caa0da6c3d3866d8e97a45a2219dbb07d`.
  Exact head `de5ce80ffc09cac27df33bc1ed5853f80e675ddc`:
  [CI38236381786](https://github.com/tya5/chrona/actions/runs/38236381786)
  passes conformance, three pytest shards, MCP floor and newest-Python reproduction.
- [CI artifact11740801951](https://github.com/tya5/chrona/actions/runs/38236381786/artifacts/11740801951):
  all 92 serialized files exactly match corrected real-default local evidence.
  Focused 72 policy/pass/closure and 180 geometry/memo/history/CLI tests pass.
- Default effects remain disclosed: controller firmware-slip is a diagnosed
  summary; Editorial loses three diagnosed names; generic HALCYON loses eps
  and bus-test names. Explicit best preserves prior output. No scope was
  narrowed to claim the 60 s target or critical-route completeness.

## Architecture conclusion

Layout owns finite shapes, cheap search and rare ranked exact rescue, sharing
the declared explicit ceiling without resetting it. Best retains pair order,
ranking, validators and byte output. First-fit remains one-pass; successful
fast routes do not invoke rescue. Scene/adapters project completed geometry
and typed facts once. Specs33/50/56/66 remain consistent; no new schema version,
project-specific dispatch, surface replay or Scene geometry callback is added.
Spec50 correction `e5c7ea10` was public before implementation `8313c180`.
