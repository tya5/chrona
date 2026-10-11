<!-- chrona:literal-acceptance/v1 -->

# Issue #1420 — routing cost acceptance

Base: trusted READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
Pre-code Spec50: `345531ef`, `527f952d`; implementation: `6e7cb3fc`,
`ec540f8f`, `d1b74a31` (bounded projection working set).
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1420#issuecomment-6109953083).
Final-code measurements and PR CI/artifacts are complete. Release acceptance
still requires the exact-main three-OS run containing this review.

## Literal issue acceptance

### Issue #1420

- Source: [Issue #1420](https://github.com/tya5/chrona/issues/1420)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The existing route tests pass unchanged; any changed routes are listed and justified, as in #1298. | met | Unchanged [Scene relation families](../../../tests/unit/chrona/presentation/scene/test_relation_route_invariant.py) and Layout route families pass; [full graph/candidate/exhaustion comparison](../../../tests/unit/chrona/presentation/layout/test_route_visibility_base.py) agrees with fresh visibility. [Final-code CI38150656231](https://github.com/tya5/chrona/actions/runs/38150656231) succeeds; artifact11706855003 has46 parsed public Scene/SVG pairs, all unchanged. No changed route. | — |
| 2 | The work counters from #1298 still hold, and a new counter shows that graph builds per surface are bounded by the number of distinct obstacle sets, not by candidates. | met | Existing [quota/frontier/history counters](../../../tests/unit/chrona/presentation/layout/test_relation_search_budget.py) and [surface integration](../../../tests/integration/test_relation_search_work_bound.py) pass unchanged. New [visibility-base counter](../../../tests/unit/chrona/presentation/layout/test_route_visibility_base.py) records one base for ten distinct endpoint assemblies across equal snapshots copied before their first query, no rebuild for an excluded port, and one additional base for changed selected content. Endpoint assemblies/reverse heuristics are explicitly separate work, not called free preparation. | — |
| 3 | Output is byte-identical across two runs. | met | Completed [fixed-head benchmark recipe](../../../tests/support/routing_scale_benchmark.py) on `d1b74a31`: both200/46 and1000/228 runs exit0 and have identical raw Scene/SVG hashes, also identical to baseline; exact supplied19/10 repeats agree. Full hashes below. | — |
| 4 | The three inputs above are re-measured and reported. | met | Final-code CPU/RSS for all three inputs and both repeats are reported below and in the [measurement record](https://github.com/tya5/chrona/issues/1420#issuecomment-6109953083). Timing is evidence, not an acceptance threshold. | — |
| 5 | Do not edit `examples/**`. | met | [Base implementation](https://github.com/tya5/chrona/commit/ec540f8f13f7747046ea2df62dea28a57ddf60c6) and [projection implementation/exact supplied trial fixture](https://github.com/tya5/chrona/commit/d1b74a314081b3b0c24750a8e5a5520ecfa672f6) contain Layout and tests only; authored example diff is empty. | — |

## Programme-level criteria (optional)

Final-code combined Layout/obstacle/graph/counter/recovery/Scene relation batch:
270 tests PASS20.69s; final projection tests14 PASS0.59s. Layout float checker
PASS;11 packages/37 inward edges,228 reachable modules and0 orphans.
Only the new slice's preparation-storage assertion changes to check copy-on-write
separation at mutation; existing published route assertions are unchanged.

Layout retains exact collision/terminal/quality semantics and candidate quotas.
Shared immutable base edges are reused only for identical selected content;
monotone additions check old clear edges against every new obstacle, and new/
split edges query the full inventory. Overrides invalidate proofs. Active
input-sized geometry is surface-local and separate from the bounded search memo;
the previous-base store retains no predecessor chain. Scene/adapters are unchanged.
Projection-line facts have a16-line LRU bound (O(M) retained geometry); exact
new endpoint splits still query the full oracle. Eviction/invalidation tests
verify graph/fact identity, not only connectivity or timing.

Final-code-containing CI38150656231 (`1a3a0744`) passes all checks. Artifact11706855003:
101 paths; all46 Scene/SVG pairs parse and are byte-identical before/after;
only the code-site diagnostic inventory changes. This does not substitute for
exact-main three-OS release containing this review.

## Final-code measurements

Frozen production commit `d1b74a314081b3b0c24750a8e5a5520ecfa672f6`,
worktree-local Python3.13 venv. Benchmark repeats are terminal, not interrupted.
The supplied launch fixture is `tests/fixtures/routing_revision/project-v1.yaml`
without Actual, matching the issue's invocation. CPU is user+system seconds;
RSS is bytes. Loaded-host wall time is reported, never used as a gate.

| Objects/relations | Repeat | CPU user | CPU system | Wall seconds | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| 19/10 | 1 | 1.62 | 0.08 | 2.17 | 78069760 |
| 19/10 | 2 | 1.77 | 0.07 | 2.20 | 79314944 |
| 200/46 | 1 | 78.552974 | 0.216454 | 93.891365 | 117686272 |
| 200/46 | 2 | 77.850548 | 0.188138 | 91.296596 | 107560960 |
| 1000/228 | 1 | 3174.755976 | 8.824632 | 3707.534063 | 208781312 |
| 1000/228 | 2 | 3170.713500 | 7.664969 | 3739.551083 | 222986240 |

Baseline CPU totals:19/10=2.24;200/46=103.098832/113.487212;
1000/228=4526.29/4391.12. Baseline RSS:19/10=94175232;
200/46=94765056/75595776;1000/228=195215360/206127104.
CPU decreases; retained exact visibility/projection facts increase scale-input
peak RSS. The previous-base chain and projection working set remain explicitly
bounded by the tested design, not by a memory or wall-clock assertion.

SHA-256 (both final repeats and baseline agree):

| Input | Scene | SVG |
| --- | --- | --- |
| 19/10 | `b9f951ed43e18193cf5ed340b57d2908c92783d9140ef2d5b0dce07722ca44b4` | `b35d7eb3c0c5cb847ecbe5a36cd0ca901993b3fad974474d38d39607d468ffd1` |
| 200/46 | `d3a11cfc6fd2d7307a0dd232b48835aa08c34f7ad4969ab225ef04f60c515061` | `d948c842046388ab63a3f72cd846cde1a88ab9a7725f0a12064c63cc8ca9b66f` |
| 1000/228 | `eb688515296bb5388293e3ed5f70436b1b1ee70c8122b08a58648628622df4e5` | `3b8d641b08e778941ba53e5f0adbd859fcdbe93df47fdd6ad526bd56b3f67c08` |

Recovery already returns the baseline after a successful first trial. A real
existing recovery fixture requires different route points to recover its label;
pre-route labels change obstacles, so blindly reusing the first routes would
break the contract. No second trial is removed without equivalent full inputs.
