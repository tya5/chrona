<!-- chrona:literal-acceptance/v1 -->

# Issue #927 — derived figures acceptance

Public base: `5360a127bc8dcee13b1e5ae137475f6c9f12c704`. Design, architecture review and
implementation plan: [issue Status](https://github.com/tya5/chrona/issues/927#issuecomment-6071114520).
Implementation is on `dev-a/927-derived-figures-20261009`, not yet released.

## Literal issue acceptance

### Issue #927

- Source: [Issue #927](https://github.com/tya5/chrona/issues/927)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for whichever is taken: synthetic tests per kind and edge date, a diagnostic for a missing fact, default output unchanged, S0 gate in the PR. | not met | [Date and last-day tests](../../../tests/unit/chrona/core/test_figures.py), [closed count tests](../../../tests/unit/chrona/core/test_figure_counts.py), [scoped facts](../../../tests/unit/chrona/usecases/test_group_figures.py), [rendered labels](../../../tests/integration/test_figure_label_surfaces.py); local S0 L1/L2/L3 passed. [Corrected-head CI](https://github.com/tya5/chrona/actions/runs/37866368343) passed all checks; its 145-path snapshot preserves all 136 public SVG/Scene bytes. [Critical-path scope clarification](https://github.com/tya5/chrona/issues/927#issuecomment-6073015256), refreshed-base validation and exact-main release remain pending. | — |

## Programme-level criteria (optional)

- Covered: nine closed projected count sources, group-relative countdowns/counts, period
  `last`, literal-safe period `label.template`, and annotation-kind title/heading figures.
- Counts retain the existing behind/ahead meaning. The issue's critical-path wording is
  awaiting clarification; no forecast or critical-path endpoint delta is invented.
- Focused runs: 176 group regressions, 142 annotation regressions, 76 count/label/helper
  tests, 45 final label tests and 40 contract/fact tests passed (overlapping suites).
- Corrected-head focused suite: 117 passed, including all 18 ID-site inventory tests.
  The three figure kinds share one local ID definition without changing validation.
- S0: 443 mapped documents and 739 probes, L2+L3 40.1s; annotation lint and
  literal acceptance-review validation passed.
- Corrected-head public archive audit: all 145 paths checked, zero changed SVG/Scene
  files (136 checked), two changed diagnostic/coverage reports, no retirements.
  No corpus/preset source edits. Run 37866368343 passed conformance, MCP-floor,
  newest-Python reproduction, all three pytest shards and derived-ready. CI is not
  the scope blocker; refreshed-head PR and exact-main release evidence remain required.
- Reconciled ready base `5360a127`: 232 focused figure/label tests passed (38.25s).
  S0 passed 451 mapped documents/739 probes; L2+L3 47.9s, four invalid fixtures
  unchanged. Eight landed #849 L1 entries were proven stale and pruned; the
  seven unmerged #927 entries remain. The ordinary merge preserves both
  axis-band scale completion and annotation-header completion before text
  measurement. No figure-policy change; fresh-head artifact/CI proof remains.

## Architecture conclusion

View projection owns selection, states and count aggregation. Core consumes immutable
neutral count/date facts without importing projection types. Presentation completes
group, period and annotation strings before measurement; Layout owns geometry, Scene
and adapters carry completed content. Group and global identities are separate;
missing facts never become zero. Existing literal captions and omitted declarations
retain their contracts. Release acceptance is pending.
