<!-- chrona:literal-acceptance/v1 -->

# Release Review — flow block-size completion

Implementation: `a544b783a996398eca47ef293ab8c40dae04e347`, callback regression `c7446d3e25ae8e63b4b7367f7db307b8815c86df`; [PR #1207](https://github.com/tya5/chrona/pull/1207) and [design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1170#issuecomment-6040949170). Local focused engine/profile/cross-size tests: 84 passed, including width-dependent content callback preservation; 97 passed including conditional-radius regression after reconciling ready main576b3bdc. Conformance: 34 checks passed; diagnostic inventory alone is stale from source locations, with normalized regenerated output proven identical. CI owns regeneration.

## Literal issue acceptance

### Issue #1170

- Source: [Issue #1170](https://github.com/tya5/chrona/issues/1170)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic flow child with fixed block size N and a different preferred measurement completes at N under start and stretch. | met | [Fixed50/preferred30 start/stretch tests](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py). | — |
| 2 | Natural flow measurement and arrangement agree on that declared fixed extent, including multiple items and wrapped lines. | met | [Natural/fixed-parent, wrapped fixed children and bounded composite tests](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py): fixed50, wrapped70 and composite115 extents. | — |
| 3 | Fill/fractional children still stretch to the completed line height; intrinsic, bounded and aspect sizing obey their existing contracts. | met | [Fill/fr, flexible minimum, intrinsic/bounded and both aspect axes](https://github.com/tya5/chrona/blob/a544b783a996398eca47ef293ab8c40dae04e347/tests/unit/chrona/presentation/layout/test_flow_block_intent_completion.py); existing #1163 cross-size tests remain green. | — |
| 4 | Report actual corpus side effects without adapting examples to absorb them. | met | [Shared snapshot run37645951613](https://github.com/tya5/chrona/actions/runs/37645951613), artifact11494089916 for head91c034c4:141 exact-base paths;66 SVG+66 Scene unchanged (each slide:0 primitives changed/added/removed), remaining8 reports unchanged; diagnostic inventory source locations only. No added/retired paths, new diagnostic codes or examples edits. | — |

## Programme-level criteria (optional)

Layout applies the existing Spec33 size resolver before common flow-line formation; natural measurement and arrangement consume that closure. No Theme/View/schema/Scene/adapter ownership, diagnostics or compatibility changes. Fixed shortage retains finite placement and existing visible-overflow diagnostics. Related column sizing and [pre-existing nested flow inline-allocation defect #1206](https://github.com/tya5/chrona/issues/1206) are not silently folded into this block-size fix.
Artifact ZIP SHA-256:157f696308409cd97d4677d0970dca893f88201f893bb53a60798d139895e756; root independently verified every before blob against base576b3bdc262ae523e540128e9d982afdc9007211, exact path sets and normalized diagnostic equality. Release remains pending: final-review-head PR checks/snapshot confirmation, trusted-ready publication, and exact-review-containing-main three-OS pytest/conformance/wheel/materializer run. Earlier local or PR tests do not satisfy that release gate.
