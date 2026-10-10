<!-- chrona:literal-acceptance/v1 -->

# Issue #1271 — group-header baseline acceptance

Closed after [exact-main release](https://github.com/tya5/chrona/actions/runs/38020427654) succeeded on `0fd085d17422fd332c49b4b75ebdf43fe9459f93`, containing every literal acceptance row below. [PR #1313](https://github.com/tya5/chrona/pull/1313) merged at `0a308ba09e1bb6f26a698e6f4f93bb28fed85ad9`. [Design and architecture correction](https://github.com/tya5/chrona/issues/1271#issuecomment-6087858363). Layout reuses the table's line-box formula and translates completed header text after folded extent completion. No Scene measurement, new schemas or folded-mark allocation change.

## Literal issue acceptance

### Issue #1271

- Source: [Issue #1271](https://github.com/tya5/chrona/issues/1271)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Scene test shows the header's line box centred in the header band (tolerance 0.01 px), for both the plain and the role-marked path. | met | [Synthetic Scene/SVG test](../../../tests/integration/test_group_header_baseline.py): plain/marked, all three groups, ordinary and expanded folded headers; folded symbols retain their pitch and centered stack. | — |
| 2 | Do not edit `examples/**`. Derived sync regenerates them. The reviewer checks Marquee, Title Card and target B afterwards. | met | Only Layout, [Spec50](../../specification/50-constraint-driven-gantt-surface-quality.md), synthetic tests and this review are authored; bot regeneration and byte audit are recorded below. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) makes target adoption the reviewer's step, not a dev closing condition; reviewer completion is not claimed. | — |

## Programme-level criteria (optional)

None. Focused group/table/header batch: 219 passed (49.36s), including four new ordinary/folded Scene/SVG cases and the unchanged table centering assertion. Independent review verified the final-band translation updates both bounds and baseline without remeasurement. Scene delivery ownership passes (31 dataclasses/225 fields).

CI [37988066235](https://github.com/tya5/chrona/actions/runs/37988066235) found one stale annotation characterization hash. Independent comparison retains all 60 primitives and changes only four group-header Text bounds/baselines by +0.2 px; annotations, leaders and diagnostics are identical. Both full-byte hashes were refreshed without weakening assertions. [Exact-head CI 37993187147](https://github.com/tya5/chrona/actions/runs/37993187147) passed all three PR shards, conformance, newest-Python materializers, MCP and derived-ready.

[Exact-head artifact audit](https://github.com/tya5/chrona/pull/1313#issuecomment-6089671877): all 149 before paths match ready base `94981ebda16c75d985aa85c830b5480ea2133e42`; all 149 after paths match bot-generated main `abbe91a4`. No additions or removals; 51 SVG/Scene pairs change (206 header Text placements), plus two reports. Six leader changes and three EVB-warning removals in three slides were explicitly disclosed and visually reviewed. Automatic [derived sync](https://github.com/tya5/chrona/actions/runs/37995918964) and exact-candidate [derived-main](https://github.com/tya5/chrona/actions/runs/37997038126) succeeded.

Release evidence: the exact-main run above passed three-OS pytest, conformance and wheel/smoke, newest-Python materializers and MCP.
