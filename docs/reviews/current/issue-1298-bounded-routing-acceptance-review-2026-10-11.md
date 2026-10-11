<!-- chrona:literal-acceptance/v1 -->

# Bounded candidate routing acceptance (#1298)

Authority: Spec50 relation-instance search budget, published before code at
`4292b808`; retained-record correction published at `5b27eb43` before code.
Implementation `d2c61bcd`; scale fixtures `e9bf6e74`.
[Current architecture and implementation record](https://github.com/tya5/chrona/issues/1298#issuecomment-6094821308).

## Literal issue acceptance

### Issue #1298

- Source: [Issue #1298](https://github.com/tya5/chrona/issues/1298)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The work-unit counter test from item 3 passes and states the bound it checks. | met | [Whole-Project counter tests](../../../tests/integration/test_relation_search_work_bound.py) cover0/10/50/200 relations including composition trials; [search counter/quota tests](../../../tests/unit/chrona/presentation/layout/test_relation_search_budget.py) also cover genuine exhaustion and cache hits. For R completed instances and ≤5 passes: generator calls≤100R, frontier pops≤81920R, exact history predicates≤20R·4096²; graph preparation is recorded separately. | — |
| 2 | The existing route tests pass unchanged, or changed routes are listed and justified. | met | [Route/memo tests](../../../tests/unit/chrona/presentation/layout/test_route_memo_equivalence.py) and the placement/port, synthetic lane corridor and relation-label batch:307 passed (196.04s), unchanged expectations. Final integrated public-route deltas still need their own disposition. | — |
| 3 | The trial's 200-item/46-relation plan and 1000-item/228-relation plan both complete. The PR reports their CPU time and peak RSS (for the record, not as a gate). | not met | Corrected public source1cd70178:200 completed twice (user101.775/109.168s, peak RSS94765056/75595776B);1000 completed twice (user4509.23/4381.15s, system17.06/9.97s, peak RSS195215360/206127104B). [Completed1000 measurements](https://github.com/tya5/chrona/issues/1298#issuecomment-6108565815) and [exact public-source provenance](https://github.com/tya5/chrona/issues/1298#issuecomment-6108601657). Final integrated baseline/evidence still require acceptance. | — |
| 4 | Output stays byte-identical across two runs. | met | [Corrected200 measurements/hashes](https://github.com/tya5/chrona/issues/1298#issuecomment-6094821308) and [both completed1000 runs plus integration audit](https://github.com/tya5/chrona/issues/1298#issuecomment-6108565815) have identical Scene/SVG bytes, without restart or source mutation. Actual integrated200 output is identical too; the measured1000 routing baseline remains applicable as detailed below. | — |
| 5 | Do not edit `examples/**`. | met | [Product implementation](https://github.com/tya5/chrona/commit/d2c61bcd) and [capacity correction](https://github.com/tya5/chrona/commit/f0ec4c2c) author no examples changes. Final diff after predecessor landing must confirm this; public differences are disclosed, not absorbed into corpus edits. | — |

## Programme-level criteria (optional)

Whole-Project counters at the original implementation:
R=0/10/50/200 gives generators0/180/900/3600,
frontier pops0/16380/81900/327600, history predicates0/10820/54100/216400.
All declared relations are drawn; no relation-suppression diagnostic.

Post-M1/reviewer preparation70bf27d0 mergesc783dc73 without conflicts in a
separate worktree; the completed benchmark worktree remains unchanged. Its own
Python3.13 venv passes44 tests16.75s: whole-Project work bounds, quota/history,
exact intersection oracle and graph memo capacity. Existing route-search,
routing, obstacle index, surface routes, projection and default View bytes
are unchanged relative to the measured public1cd70178 source.
No route expectation changed. Admission bounds payload and selection records;
graph rebuilding is not charged as candidate-frontier work.

Post-M1 applicability audit at `bdc1eaf4`: actual200 CLI output is identical
to both measured outputs (98.85s user/0.20s system,105824256B peak RSS).
Read-only1000 preflight stopped at the first routing handoff, not render
completion: all content, projection, review rows, completed rows/groups/marks,
timeline/plot bounds, Layout manifest, metrics, text and obstacle inventory
are identical. Both normalized captures hash
`713aa05458194a21142fd61d8dad7db08d0f703b860453d61296c1833a881a86`;
950 marks,2860 obstacles,150 unpainted simple symbol parts. Routing, member-label,
route-label, adapter and default resource bytes are unchanged. Annotation changes
are inactive; host identity preserves the existing formula for these simple
parts. This supports using the named completed1000 measurements; it does not
claim a newly completed1000 render on the integrated source.
[Published measurements and applicability facts](https://github.com/tya5/chrona/issues/1298#issuecomment-6108565815).

**Release pending:** final READY adoption, PR publication of measured results,
batched public-artifact changes with reasons, current-head PR
gates and exact acceptance-containing main three-OS release. Do not close.

## Architecture conclusion

Layout completes geometry with existing safety, quality, rank and tie rules.
Deterministic quotient/remainder quotas replace the per-pair4096 reset; an
immutable branch-local index retains the exact history predicate. Finite
graph work remains obstacle-dependent, not falsely constant. Search exhaustion
is not proof of geometric impossibility; #1300 must preserve that distinction
when implementing protected critical routing. Scene/adapters do not search.
