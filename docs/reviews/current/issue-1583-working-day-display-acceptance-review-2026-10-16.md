<!-- chrona:literal-acceptance/v1 -->

# Issue #1583 — working-day display and comparison

Core date handling is published in PR1599; the remaining packaged declarations
are integrated in [PR1623](https://github.com/tya5/chrona/pull/1623), merged at
`340b9e708b4047eb02f83295427e2756aa56a50d`, followed by ready derived main
`fa262ebab648229138eb34c33bf6a821f6450e96`.
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
| 2 | The #1582 CSV renders `05 Oct – 09 Oct` and `0` for `test-plan` in the default draft and `target-b`, viewed as PNG. | met | Current after-snapshot evidence for exact PR head `9ff8b12a8a932b09d1c6a7be9ada154c77b84ad0`: all 15 preset Test plan rows match the viewed matrix from the unchanged [CSV](https://github.com/tya5/chrona/issues/1582); default `05 Oct – 09 Oct` / `+0d`, shipped target-b `+0d`, executive-light `+0d`; no invented Plan column. Each declared comparison shows its formatted zero, never `-2d`; Editorial declares no visible comparison. | — |
| 3 | Public SVG/Scene changes are listed with counts in the PR. | met | [PR1623](https://github.com/tya5/chrona/pull/1623) lists per-slide primitive/diagnostic counts for [artifact 12090006524](https://github.com/tya5/chrona/actions/runs/39002549459/artifacts/12090006524): 109 paths, 0 added/retired; SVG 32 changed/18 identical; Scene 34 changed/16 identical; 0 dependency primitives removed. The current after-snapshot bytes match the viewed evidence. | — |

## Programme-level criteria (optional)

The canonical calendar basis and shared date helper own arithmetic; View
declares deltaUnit, Layout formats completed facts, Scene/adapters serialize.
No project/preset-ID branch, core half-open date change or schema migration.
Eight legacy declarations now select working-days; explicit calendar-days
still produces the intended civil delta. Exact-head PR CI run
[39002549459](https://github.com/tya5/chrona/actions/runs/39002549459) is green.
The exact-main three-OS release [39003719153](https://github.com/tya5/chrona/actions/runs/39003719153)
is live; its result is pending, so release acceptance and issue closure remain
pending.
