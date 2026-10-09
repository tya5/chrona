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

Required release evidence: ready-main base, exact-head PR checks, artifact per-slide header-position counts and unrelated-byte audit, automatic derived sync, then exact-main three-OS pytest/conformance/wheel with this review published. Do not close before those gates.
