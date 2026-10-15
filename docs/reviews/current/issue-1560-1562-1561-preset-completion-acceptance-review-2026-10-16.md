<!-- chrona:literal-acceptance/v1 -->

# Generic preset completion — acceptance review

This is not release acceptance. Individual PRs and their public artifact
comparisons are recorded below; the combined candidate and exact-main release
still require their own gates. Unmet criteria keep the corresponding issue open.

## Literal issue acceptance

### Issue #1560

- Source: [Issue #1560](https://github.com/tya5/chrona/issues/1560)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests for `select: all`: none, one and several periods, in declaration order. | met | [Period selection tests](../../../tests/integration/test_all_periods.py), [PR #1574](https://github.com/tya5/chrona/pull/1574). | — |
| 2 | On halcyon-1, `render --preset target-b\|yuya\|titlecard\|marquee\|sunday` draws the launch window band and the three notes in each design's form, viewed as PNG. Report any design whose placement fails with counts; do not tune design YAML in the PR. | met | [PR count table and PNG inspection](https://github.com/tya5/chrona/pull/1574): all five have one band/label and three notes; Sunday has two overlapping notes, reported without tuning.30/30 named renders succeed. | [Placement quality #1568](https://github.com/tya5/chrona/issues/1568) |
| 3 | Projects without periods or notes are byte-identical. The schema equivalence result and the gap-record rows are updated. | not met | [PR #1574](https://github.com/tya5/chrona/pull/1574): all15empty-control SVGs and completed placements/diagnostics identical, but five Scenes change only View source identity. [Disposition requested](https://github.com/tya5/chrona/issues/1560#issuecomment-6194180037). Full equivalence PASS and gap updates are published; this does not waive the byte wording. | — |

### Issue #1562

- Source: [Issue #1562](https://github.com/tya5/chrona/issues/1562)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests for each shape and for the size token, present and absent. | met | [Legend shape/size integration tests](../../../tests/integration/test_legend_swatch_shapes.py), [contract tests](../../../tests/unit/chrona/presentation/contracts/test_legend_swatch_contract.py), [PR #1575](https://github.com/tya5/chrona/pull/1575). | — |
| 2 | wallboard-dark and technical-print PNGs show circles, a rule pair and larger chevrons. | met | [PR #1575 PNG inspection](https://github.com/tya5/chrona/pull/1575): fresh independent-base renders show five authored circles, six unchanged square palette keys, larger native chevrons and the technical-print vertical rule pair. No claim of a generated-key shape API. | — |
| 3 | All public SVG and Scene files are byte-identical. | not met | [Exact-head artifact11984999982](https://github.com/tya5/chrona/actions/runs/38761253611/artifacts/11984999982) at085e72c27:50SVG identical;11of50Scenes omit unused rounded-diamond `pathCommands` from336Symbols. Actual `symbol.outline`, routes, IDs, diagnostics and provenance unchanged. [Migration disposition](https://github.com/tya5/chrona/issues/1562#issuecomment-6195809113) pending; misleading geometry is not restored for compatibility. | — |

### Issue #1561

- Source: [Issue #1561](https://github.com/tya5/chrona/issues/1561)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a chain with a critical path and a non-critical branch; the role present or absent. | met | [Real Scheduler integration](../../../tests/integration/test_timeline_critical_role.py), [critical-fact and default-off tests](../../../tests/unit/chrona/presentation/review/test_v05_content.py), [PR #1576](https://github.com/tya5/chrona/pull/1576). | — |
| 2 | `render --preset muted-executive` on halcyon-1 shows heavier critical relations, viewed as PNG. | not met | [PNG evidence and decision request](https://github.com/tya5/chrona/issues/1561#issuecomment-6194934913): HALCYON has no canonical critical objects and correctly shows24ordinary/0critical relations. Neutral chain PNG shows two critical width2 and two ordinary width1 edges. No classification or Project data is fabricated. | — |
| 3 | All public SVG and Scene files are byte-identical. | met | [Exact-head artifact11984004378](https://github.com/tya5/chrona/actions/runs/38759593755/artifacts/11984004378) atf028e65dd:50SVG+50Scene raw bytes identical,0added/retired; only diagnostic-source-line report changes. | — |

## Programme-level criteria (optional)

The three independent PRs must be green before integration publication. The
integration candidate must pass its own CI and public-artifact review, then
exact-main three-OS release containing these reviews. None is inferred from
an older green run or an artifact-only comparison.

Release prerequisite: [main run38757817385](https://github.com/tya5/chrona/actions/runs/38757817385)
passed Ubuntu/macOS but failed26Windows TikZ tests because native backslashes
were validated before existing POSIX path serialization. The
[published repair plan](https://github.com/tya5/chrona/issues/1553#issuecomment-6196104996)
aligns the safety check with that serialization, retaining unsafe-character,
suffix, face-index and existence checks. Host-independent Windows-path controls
cover safe spaces and unsafe directories/filenames; native Windows release CI
is still required. Font ordering, measurement and Layout/Scene are unchanged.

## Architecture conclusion

Content closes period selection and canonical critical-role intent before
Layout. Layout owns all completed geometry; Scene owns keyed paint projection
and clears transient legend intent before export. Adapters do not place shapes
or classify criticality. No examples or generated outputs were hand-edited.
There is no issue-closure recommendation while its literal row is not met.
