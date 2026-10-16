<!-- chrona:literal-acceptance/v1 -->

# Issue #1583 — working-day display and comparison

Product source `fa14587ab`, combined source `feaae2185`, ready base
`e02bcf5a1097d2c6b4a8f85c53376704906dcb70` (includes #1584).
[Approved design/implementation plan](https://github.com/tya5/chrona/issues/1583#issuecomment-6203710183)
and [calendarless policy](https://github.com/tya5/chrona/issues/1583#issuecomment-6217533121).
This is not release acceptance: final-head CI, row2 disposition
and exact-main three-OS release remain required.

## Literal issue acceptance

### Issue #1583

- Source: [Issue #1583](https://github.com/tya5/chrona/issues/1583)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: 5wd from Monday shows Friday; actual Friday finish shows variance 0; calendar-day (`d`) items unchanged; a holiday exception before the end. | met | [Date basis tests](../../../tests/unit/chrona/presentation/model/test_working_day_date_basis.py) and [projection/table tests](../../../tests/unit/chrona/presentation/model/test_working_day_projection.py): working/civil spans, holiday/override/calendarless/signed distance controls, Friday Actual zero, Actual weekend civil closure, source-local snapshot/scenario calendars, raw dates unchanged. [Defaults tests](../../../tests/integration/test_view_defaults.py) preserve explicit calendar-days. | — |
| 2 | The #1582 CSV renders `05 Oct – 09 Oct` and `0` for `test-plan` in the default draft and `target-b`, viewed as PNG. | not met | Root viewed exact-CSV default draft PNG with05Oct–09Oct/+0d and target-b with+0d. Target-b ships no Plan column; a scratch authored View adding its existing dateRange/inclusive column also visibly shows05Oct–09Oct/+0d. [Reviewer clarification requested](https://github.com/tya5/chrona/issues/1583#issuecomment-6217961113); no silent design change or acceptance relaxation. | — |
| 3 | Public SVG/Scene changes are listed with counts in the PR. | met | [PR count table](https://github.com/tya5/chrona/pull/1599), [source4ff4ba2e1 artifact12054151992](https://github.com/tya5/chrona/actions/runs/38918644054/artifacts/12054151992):109 paths before/after,0 added/retired;5 SVG/9 Scene/3 reports changed. Each HALCYON21–25 has4 changed variance Text records, no primitive additions/removals;4 roadmap Scenes change metadata only;41 other contexts unchanged. All route/mark/annotation geometry and diagnostics unchanged; SVG non-text elements independently identical. Refresh audit on the final reconciled head. | — |

## Programme-level criteria (optional)

Architecture review: Core half-open dates remain unchanged. One source-local
typed basis and shared date helper feed canonical projection comparison facts
and pre-Layout display ranges. Scene/adapters perform no calendar arithmetic.
Calendarless presentation counts civil days without warning. Specifications06/24
and shared vocabulary express the contract; default policy is declared in YAML,
never selected by preset ID. Focused205 tests pass; schema equivalence against
ready main passes (delta1/equal37,575 corpus documents,739 probes;L2+L3=22.1s
within60s). Combined hierarchy/date/policy/routing/coverage controls pass106 tests;
the earlier policy-fixture batch passes84+18 tests. Independent combined-merge
review found no dropped policy, source-local basis, diagnostic or ownership rule.
