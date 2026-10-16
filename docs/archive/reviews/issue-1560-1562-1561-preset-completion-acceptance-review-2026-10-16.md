<!-- chrona:literal-acceptance/v1 -->

# Generic preset completion — acceptance review

The review-containing main commit `7ca7e5553244b1e726730ad07304c08562cf93d6`
passed the three-OS release matrix, conformance, wheel, newest-Python
materializer and MCP checks in [release38814769736](https://github.com/tya5/chrona/actions/runs/38814769736).

## Literal issue acceptance

### Issue #1560

- Source: [Issue #1560](https://github.com/tya5/chrona/issues/1560)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests for `select: all`: none, one and several periods, in declaration order. | met | [Period selection tests](../../../tests/integration/test_all_periods.py), [PR #1574](https://github.com/tya5/chrona/pull/1574). | — |
| 2 | On halcyon-1, `render --preset target-b\|yuya\|titlecard\|marquee\|sunday` draws the launch window band and the three notes in each design's form, viewed as PNG. Report any design whose placement fails with counts; do not tune design YAML in the PR. | met | [PR count table and PNG inspection](https://github.com/tya5/chrona/pull/1574): all five have one band/label and three notes; Sunday has two overlapping notes, reported without tuning.30/30 named renders succeed. | [Placement quality #1581](https://github.com/tya5/chrona/issues/1581) |
| 3 | Projects without periods or notes are byte-identical. The schema equivalence result and the gap-record rows are updated. | met | The reviewer confirms the intended boundary is source `contentIdentity` provenance: visible output and completed primitives/diagnostics of the empty control are unchanged ([decision](https://github.com/tya5/chrona/issues/1560#issuecomment-6202896850)). The 15-onboarding comparison found this provenance-only Scene difference; full schema equivalence and gap updates are published in [PR #1574](https://github.com/tya5/chrona/pull/1574). | — |

### Issue #1562

- Source: [Issue #1562](https://github.com/tya5/chrona/issues/1562)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests for each shape and for the size token, present and absent. | met | [Legend shape/size integration tests](../../../tests/integration/test_legend_swatch_shapes.py), [contract tests](../../../tests/unit/chrona/presentation/contracts/test_legend_swatch_contract.py), [PR #1575](https://github.com/tya5/chrona/pull/1575). | — |
| 2 | wallboard-dark and technical-print PNGs show circles, a rule pair and larger chevrons. | met | [PR #1575 PNG inspection](https://github.com/tya5/chrona/pull/1575): fresh independent-base renders show five authored circles, six unchanged square palette keys, larger native chevrons and the technical-print vertical rule pair. No claim of a generated-key shape API. | — |
| 3 | Original: All public SVG and Scene files are byte-identical. Revised by reviewer: all public SVG files are identical; the only Scene change is omission of redundant rounded-diamond `pathCommands` from 336 Symbols in 11 Scene files. | met | Reviewer accepted the 11-file/336-field removal as the intended correction because `symbol.outline` and every SVG remain identical ([disposition](https://github.com/tya5/chrona/issues/1562#issuecomment-6202897618)). Exact-head [artifact11984999982](https://github.com/tya5/chrona/actions/runs/38761253611/artifacts/11984999982) at `085e72c27` records 50 identical SVGs and those 11 Scene changes only. The new Theme default for generated-key shapes is successor [#1580](https://github.com/tya5/chrona/issues/1580), not a blocker for this row. | [#1580](https://github.com/tya5/chrona/issues/1580) |

### Issue #1561

- Source: [Issue #1561](https://github.com/tya5/chrona/issues/1561)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a chain with a critical path and a non-critical branch; the role present or absent. | met | [Real Scheduler integration](../../../tests/integration/test_timeline_critical_role.py), [critical-fact and default-off tests](../../../tests/unit/chrona/presentation/review/test_v05_content.py), [PR #1576](https://github.com/tya5/chrona/pull/1576). | — |
| 2 | Original: `render --preset muted-executive` on halcyon-1 shows heavier critical relations, viewed as PNG. Revised by reviewer: the named preset on a neutral synthetic chain shows two critical width-2 and two ordinary width-1 relations, viewed as PNG; HALCYON has zero critical relations and no regression. | met | Reviewer accepted the synthetic witness because HALCYON's canonical critical set is empty under Spec57; relabeling slack edges would be incorrect ([revised disposition](https://github.com/tya5/chrona/issues/1561#issuecomment-6202897214)). Both PNGs were inspected. | — |
| 3 | All public SVG and Scene files are byte-identical. | met | [Exact-head artifact11984004378](https://github.com/tya5/chrona/actions/runs/38759593755/artifacts/11984004378) atf028e65dd:50SVG+50Scene raw bytes identical,0added/retired; only diagnostic-source-line report changes. | — |

## Architecture conclusion

Content closes period selection and canonical critical-role intent before
Layout. Layout owns all completed geometry; Scene owns keyed paint projection
and clears transient legend intent before export. Adapters do not place shapes
or classify criticality. No examples or generated outputs were hand-edited.
Acceptance and closure are recorded by the review-containing release above.
Successor #1580 tracks the generated-key default independently.
