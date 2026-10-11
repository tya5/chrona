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
| 2 | The existing route tests pass unchanged, or changed routes are listed and justified. | met | Existing route/memo/placement/port, synthetic lane corridor and relation-label batch:307 passed (196.04s), unchanged expectations. Final integrated public-route deltas still need their own disposition. | — |
| 3 | The trial's 200-item/46-relation plan and 1000-item/228-relation plan both complete. The PR reports their CPU time and peak RSS (for the record, not as a gate). | not met | [Measurements](https://github.com/tya5/chrona/issues/1298#issuecomment-6094821308):200 completed twice, user CPU112.281/110.814s, peak RSS140902400/396820480B;1000 terminated by signal9 after8542.826s wall/1718.453s user CPU, reported RSS349536256B. Termination cause unconfirmed. Both sizes must rerun after the capacity correction and final integration. | — |
| 4 | Output stays byte-identical across two runs. | not met | The two200 renders have identical Scene/SVG hashes;1000 did not complete. Corrected final-base repeated bytes remain required. | — |
| 5 | Do not edit `examples/**`. | met | Authored branch diff against `origin/main` contains no `examples/**` path. Public differences must be disclosed, not absorbed into authored examples. | — |

## Programme-level criteria (optional)

Quota/history/placement batch:38 passed (13.24s). Whole-Project counters:
4 passed (107.23s); R=0/10/50/200 gives generators0/180/900/3600,
frontier pops0/16380/81900/327600, history predicates0/10820/54100/216400.
All declared relations are drawn; no relation-suppression diagnostic.

Retained-record correction: existing memo/history/quota/intersection tests71
passed; new capacity tests3 passed after fixing the new harness to compare
search-limit outcomes as well as candidates. Whole-Project counters4 passed
(22.92s). READY9ea350d5 and public #1292 correction71a27210 adopted; combined
cache/legend/date/scope/schema-ID/ownership tests55 passed (21.52s). No existing
route expectation changed. Admission bounds payload and selection records;
graph rebuilding is not charged as candidate-frontier work. Actual scale
completion is still unproved, not implied by these unit and counter tests.

**Release pending:** final predecessor integration, scale measurements and
repeated bytes, batched public-artifact changes with reasons, current-head PR
gates and exact acceptance-containing main three-OS release. Do not close.

## Architecture conclusion

Layout completes geometry with existing safety, quality, rank and tie rules.
Deterministic quotient/remainder quotas replace the per-pair4096 reset; an
immutable branch-local index retains the exact history predicate. Finite
graph work remains obstacle-dependent, not falsely constant. Search exhaustion
is not proof of geometric impossibility; #1300 must preserve that distinction
when implementing protected critical routing. Scene/adapters do not search.
