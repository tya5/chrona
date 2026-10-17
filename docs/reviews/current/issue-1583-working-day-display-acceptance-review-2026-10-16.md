<!-- chrona:literal-acceptance/v1 -->

# Issue #1583 — working-day display and comparison

Core date handling is published in PR1599; the remaining packaged declarations
are integrated in [PR1623](https://github.com/tya5/chrona/pull/1623), based on ready
`9d888beb7468739b68e35de8b1d0ade79cf0ff56`.
[Approved design/implementation plan](https://github.com/tya5/chrona/issues/1583#issuecomment-6203710183),
[calendarless policy](https://github.com/tya5/chrona/issues/1583#issuecomment-6217533121),
and [shipped target-b clarification](https://github.com/tya5/chrona/issues/1583#issuecomment-6222305552).

## Literal issue acceptance

### Issue #1583

- Source: [Issue #1583](https://github.com/tya5/chrona/issues/1583)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: 5wd from Monday shows Friday; actual Friday finish shows variance 0; calendar-day (`d`) items unchanged; a holiday exception before the end. | met | [Date basis](../../../tests/unit/chrona/presentation/model/test_working_day_date_basis.py), [projection](../../../tests/unit/chrona/presentation/model/test_working_day_projection.py) and [packaged label controls](../../../tests/integration/test_packaged_working_day_labels.py): inclusive Friday, civil/working spans, holidays, calendarless behavior, Friday/weekend Actual zero, lanes/automatic and explicit calendar-days override. | — |
| 2 | The #1582 CSV renders `05 Oct – 09 Oct` and `0` for `test-plan` in the default draft and `target-b`, viewed as PNG. | met | Root viewed all15preset Test plan rows from the unchanged [CSV](https://github.com/tya5/chrona/issues/1582) in `/tmp/chrona-1610-current-matrix.1xD6Q4/review-rows-{1,2,3}.png` at product712e7240f: default05Oct–09Oct/+0d, shipped target-b+0d, executive-light+0d; no invented Plan column. Each declared comparison shows its formatted zero, never-2d; Editorial declares no visible comparison. | — |
| 3 | Public SVG/Scene changes are listed with counts in the PR. | not met | [PR1599](https://github.com/tya5/chrona/pull/1599) has the published core-stage counts. Final combined declarations/placement need a fresh official [PR1623](https://github.com/tya5/chrona/pull/1623) snapshot and count table; earlier-stage counts are not final evidence. | — |

## Programme-level criteria (optional)

The canonical calendar basis and shared date helper own arithmetic; View
declares deltaUnit, Layout formats completed facts, Scene/adapters serialize.
No project/preset-ID branch, core half-open date change or schema migration.
Eight legacy declarations now select working-days; explicit calendar-days
still produces the intended civil delta. Final exact-head CI, public counts
and the review-containing main three-OS release remain required before closure.
