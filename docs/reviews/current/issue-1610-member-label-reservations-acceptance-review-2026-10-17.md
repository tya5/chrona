<!-- chrona:literal-acceptance/v1 -->

# Issue #1610 — paint-safe member-label reservations

Product corrections `aa02fe2f3`, `0d2b0f902`, `879b45790` and `7e9616f49`,
integrated with ready main `9d888beb7468739b68e35de8b1d0ade79cf0ff56`.
[PR #1623](https://github.com/tya5/chrona/pull/1623);
[living design, architecture and implementation record](https://github.com/tya5/chrona/issues/1610#issuecomment-6227031513).
Spec33 correction `027e5c5cc` was published before the unified scheduler.

## Literal issue acceptance

### Issue #1610

- Source: [Issue #1610](https://github.com/tya5/chrona/issues/1610)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin of the crossing case. | met | [Trace](https://github.com/tya5/chrona/issues/1610#issuecomment-6225778103); [reservation/required-label twins](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_plan.py), [painted paths](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_stroke.py), [bounded search](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py) and [neutral completed outcomes](../../../tests/integration/test_completed_annotation_label_outcomes.py). Focused search/topology/diagnostic/ownership batch:63 passed; additional route coordination and phase controls pass. | — |
| 2 | The two presets on the #1582 CSV draw no label crossed by a route or the as-of line, viewed as PNG. | met | Root re-rendered/viewed the unchanged [public CSV](https://github.com/tya5/chrona/issues/1582) with both presets. Current PNG/Scene pairs: `/tmp/chrona-1610-acceptance-75J1TZ/{default,executive-light}-fair.*`; both requested names visible, actual-width dependency/as-of intersections0 (default13names/14dependency primitives; executive11/13). | — |
| 3 | Public SVG/Scene changes listed with counts. | not met | Initial [artifact12083134379](https://github.com/tya5/chrona/actions/runs/38988103045/artifacts/12083134379) and follow-up [artifact12084960551](https://github.com/tya5/chrona/actions/runs/38989920511/artifacts/12084960551) disclose39SVG+39Scene changes,11+11identical, no added/retired paths or dependency primitives. The subsequent fair-tail correction needs a fresh final snapshot/count table; those earlier counts are not claimed as current-head evidence. | — |

## Programme-level criteria (optional)

Release is not accepted until the final public snapshot/counts, exact-head CI
and exact review-containing main three-OS release pass. The prior CI's8failures
are addressed locally: four deliberately refreshed CLI records and four
display witnesses corrected without waiving their actual contracts.

Layout alone owns reservations, required-label identity, bounded retries,
actual-paint validation and atomic annotation geometry. Ordinary and opposite-side
strict tails share one fair scheduler; only the latter may exempt the exact
as-of rule on its routed centerline. The direct tail, box order, aggregate1024
route-state cap, independent box cap, quality bounds and other safety checks
remain unchanged. The ordinary depth-first prefix intentionally changes.
Its unused batch-search wrapper is removed; Scene/adapters gain no policy.

HALCYON02 now retains all three connected tails: window direct, TVAC/station
routed. The full geometric/determinism/budget test passes, and root viewed
`/tmp/chrona-1610-fair-tail-validation/programme-board-fair.png`.
Both direct and routed tails meet the accepted C3 topology contract; no tail
or obstacle assertion is removed. DVT follows its declared inside/above ladder
with exact host, stroke clearance and contrast checks. Firmware may fit instead
of being suppressed; coherent visible-or-summary outcomes and byte-identical
end/finish aliases are required, with neutral visible and forced-suppression twins.

Measured routing tradeoff (ready8c4 versus initial productec4, same HALCYON
programme-board input):1call/0.493s→3calls/8.253s; whole profile2.986→11.143s,
wall3.65→12.00s. This is a disclosed bounded accuracy cost, not a target or
a current-head benchmark. No unsafe cross-inventory cache or hidden quota
increase is introduced. Final public route/name/annotation deltas remain a gate.
