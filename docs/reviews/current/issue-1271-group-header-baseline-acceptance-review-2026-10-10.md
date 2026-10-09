<!-- chrona:literal-acceptance/v1 -->

# Issue #1271 — group-header baseline acceptance

Implementation: [PR #1313](https://github.com/tya5/chrona/pull/1313), reviewed head `efc4cabd1a6a79374c4a5998bb3cbfbb7b22496d`, merged at `0a308ba09e1bb6f26a698e6f4f93bb28fed85ad9`; ready generated main `abbe91a40b46621e448eded6dcfb42b1dd97bb7b`. [Selected design and architecture correction](https://github.com/tya5/chrona/issues/1271#issuecomment-6087858363). Layout reuses the table's exact line-box formula and translates completed header text after folded extent completion. No Scene measurement, new schemas or folded-mark allocation change. Final review publication and exact-main release remain pending; do not close.

## Literal issue acceptance

### Issue #1271

- Source: [Issue #1271](https://github.com/tya5/chrona/issues/1271)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Scene test shows the header's line box centred in the header band (tolerance 0.01 px), for both the plain and the role-marked path. | met | [Synthetic Scene/SVG test](../../../tests/integration/test_group_header_baseline.py): plain/marked, all three groups, ordinary and expanded folded headers; folded symbols retain their pitch and centered stack. | — |
| 2 | Do not edit `examples/**`. Derived sync regenerates them. The reviewer checks Marquee, Title Card and target B afterwards. | met | Only Layout, [Spec50](../../specification/50-constraint-driven-gantt-surface-quality.md), synthetic tests and this review change. No examples or generated evidence authored. Public change counts and bot regeneration remain release gates below. | — |

## Programme-level criteria (optional)

None. Focused group/table/header batch: 219 passed (49.36s), including four new ordinary/folded Scene/SVG cases and the unchanged table centering assertion. Independent review verified the final-band translation updates both bounds and baseline without remeasurement. Scene delivery ownership passes (31 dataclasses/225 fields).

CI [37988066235](https://github.com/tya5/chrona/actions/runs/37988066235) found one stale annotation characterization hash. Independent comparison retains all 60 primitives and changes only four group-header Text bounds/baselines by +0.2 px; annotations, leaders and diagnostics are identical. Both full-byte hashes were refreshed without weakening assertions. [Exact-head CI 37993187147](https://github.com/tya5/chrona/actions/runs/37993187147) passed all three PR shards, conformance, newest-Python materializers, MCP and derived-ready.

[Exact-head artifact audit](https://github.com/tya5/chrona/pull/1313#issuecomment-6089671877): all 149 before paths match ready base `94981ebda16c75d985aa85c830b5480ea2133e42`; all 149 after paths match bot-generated main `abbe91a4`. No additions or removals; 51 SVG/Scene pairs change (206 header Text placements), plus two reports. Six leader changes and three EVB-warning removals in three slides were explicitly disclosed and visually reviewed. Automatic [derived sync](https://github.com/tya5/chrona/actions/runs/37995918964) and exact-candidate [derived-main](https://github.com/tya5/chrona/actions/runs/37997038126) succeeded.

Required release evidence: publication of this final review, then successful three-OS pytest/conformance/wheel on the exact published main containing it. Main run [37997952000](https://github.com/tya5/chrona/actions/runs/37997952000) tests the product candidate, not this updated review, and cannot alone close the issue.
