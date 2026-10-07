<!-- chrona:literal-acceptance/v1 -->

# Release Review — flow block-size completion

Implementation: `a544b783a996398eca47ef293ab8c40dae04e347`; [design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1170#issuecomment-6040949170). Local focused engine/profile/cross-size tests: 84 passed, including width-dependent content callback preservation. Conformance: 34 checks passed; diagnostic inventory alone is stale from source locations, with normalized regenerated output proven identical. CI owns regeneration.

## Literal issue acceptance

### Issue #1170

- Source: [Issue #1170](https://github.com/tya5/chrona/issues/1170)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic flow child with fixed block size N and a different preferred measurement completes at N under start and stretch. | met | [Fixed50/preferred30 start/stretch tests](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py). | — |
| 2 | Natural flow measurement and arrangement agree on that declared fixed extent, including multiple items and wrapped lines. | met | [Natural/fixed-parent, wrapped fixed children and bounded composite tests](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py): fixed50, wrapped70 and composite115 extents. | — |
| 3 | Fill/fractional children still stretch to the completed line height; intrinsic, bounded and aspect sizing obey their existing contracts. | met | [Fill/fr, flexible minimum, intrinsic/bounded and both aspect axes](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py); existing #1163 cross-size tests remain green. | — |
| 4 | Report actual corpus side effects without adapting examples to absorb them. | not met | [Planned CI shared snapshot review](https://github.com/tya5/chrona/issues/1170#issuecomment-6040949170) is pending; no examples edits. Replace this row with the actual artifact receipt and per-slide counts before acceptance. | — |

## Programme-level criteria (optional)

Layout applies the existing Spec33 size resolver before common flow-line formation; natural measurement and arrangement consume that closure. No Theme/View/schema/Scene/adapter ownership, diagnostics or compatibility changes. Fixed shortage retains finite placement and existing visible-overflow diagnostics. Related column sizing and [pre-existing nested flow inline-allocation defect #1206](https://github.com/tya5/chrona/issues/1206) are not silently folded into this block-size fix.
Release remains pending: actual shared-snapshot review, final PR checks, trusted-ready publication, and exact-review-containing-main three-OS pytest/conformance/wheel/materializer run. Earlier local or PR tests do not satisfy that release gate.
