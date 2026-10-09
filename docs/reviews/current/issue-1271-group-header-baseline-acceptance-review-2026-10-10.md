<!-- chrona:literal-acceptance/v1 -->

# Issue #1271 — group-header baseline acceptance

Implementation: `20e22d0b`, based on adopted ready main `0617e671c51ed14fe0d242a37a18a744bd85b7e8` (#927 merged). [Selected design and architecture correction](https://github.com/tya5/chrona/issues/1271#issuecomment-6087858363). Layout reuses the table's exact line-box formula and translates completed header text after folded extent completion. No Scene measurement, new schemas or folded-mark allocation change. Exact-head and release gates remain pending.

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

CI [37988066235](https://github.com/tya5/chrona/actions/runs/37988066235) found one stale annotation characterization hash. Independent before/after comparison retains all 60 primitives and changes only four group-header Text bounds/baselines by +0.2 px; annotations, leaders and diagnostics are identical. Both full-byte hashes are refreshed without weakening assertions. [Exact-head public artifact audit](https://github.com/tya5/chrona/pull/1313#issuecomment-6089006948) records the approved output changes.

Required release evidence: refreshed ready-main base and exact-head PR checks, automatic derived sync, then exact-main three-OS pytest/conformance/wheel with this review published. Do not close before those gates.
