<!-- chrona:literal-acceptance/v1 -->

# Issue #1420 — routing cost acceptance

Base: trusted READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
Pre-code Spec50: `345531ef`; implementation: `6e7cb3fc`, `ec540f8f`.
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1420#issuecomment-6109953083).
No release acceptance: fixed-head measurements and current-head CI/artifacts remain pending.

## Literal issue acceptance

### Issue #1420

- Source: [Issue #1420](https://github.com/tya5/chrona/issues/1420)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The existing route tests pass unchanged; any changed routes are listed and justified, as in #1298. | met | Unchanged [Scene relation families](../../../tests/unit/chrona/presentation/scene/test_relation_route_invariant.py) and Layout route families pass; [full graph/candidate/exhaustion comparison](../../../tests/unit/chrona/presentation/layout/test_route_visibility_base.py) agrees with fresh visibility. Preliminary 200/46 Scene/SVG hashes match the baseline. Current-head public corpus/CI remains required. | — |
| 2 | The work counters from #1298 still hold, and a new counter shows that graph builds per surface are bounded by the number of distinct obstacle sets, not by candidates. | met | Existing [quota/frontier/history counters](../../../tests/unit/chrona/presentation/layout/test_relation_search_budget.py) and [surface integration](../../../tests/integration/test_relation_search_work_bound.py) pass unchanged. New [visibility-base counter](../../../tests/unit/chrona/presentation/layout/test_route_visibility_base.py) records one base for ten distinct endpoint assemblies across equal snapshots copied before their first query, no rebuild for an excluded port, and one additional base for changed selected content. Endpoint assemblies/reverse heuristics are explicitly separate work, not called free preparation. | — |
| 3 | Output is byte-identical across two runs. | not met | [Fixed-head two-run benchmark recipe](../../../tests/support/routing_scale_benchmark.py) is running on `ec540f8f`; preliminary prior slice repeated 200/46 hashes agree, but final-head complete measurements are pending in the [work record](https://github.com/tya5/chrona/issues/1420#issuecomment-6109953083). | — |
| 4 | The three inputs above are re-measured and reported. | not met | [Measurement record](https://github.com/tya5/chrona/issues/1420#issuecomment-6109953083): preliminary 200/46 CPU/RSS and baseline are reported. Final 200/46, 1000/228 and the exact supplied launch plan remain required; preliminary numbers are not final acceptance. | — |
| 5 | Do not edit `examples/**`. | met | [Implementation scope](https://github.com/tya5/chrona/commit/ec540f8f13f7747046ea2df62dea28a57ddf60c6) contains Layout and synthetic tests only. | — |

## Programme-level criteria (optional)

Focused final-code batches:141 Layout/obstacle/graph/counter/recovery tests PASS
15.93s;126 existing Scene relation tests PASS5.01s. Layout float checker PASS.
Only the new slice's preparation-storage assertion changes to check copy-on-write
separation at mutation; existing published route assertions are unchanged.

Layout retains exact collision/terminal/quality semantics and candidate quotas.
Shared immutable base edges are reused only for identical selected content;
monotone additions check old clear edges against every new obstacle, and new/
split edges query the full inventory. Overrides invalidate proofs. Active
input-sized geometry is surface-local and separate from the bounded search memo;
the previous-base store retains no predecessor chain. Scene/adapters are unchanged.

Recovery already returns the baseline after a successful first trial. A real
existing recovery fixture requires different route points to recover its label;
pre-route labels change obstacles, so blindly reusing the first routes would
break the contract. No second trial is removed without equivalent full inputs.
