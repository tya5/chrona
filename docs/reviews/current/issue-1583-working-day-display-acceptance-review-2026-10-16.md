<!-- chrona:literal-acceptance/v1 -->

# Issue #1583 — working-day display and comparison

Product source `fa14587ab`, reconciled source `68e9ce296`, ready base
`b28afc8cf2cca1fd24d87ea0815305d94c3e5351`.
[Approved design/implementation plan](https://github.com/tya5/chrona/issues/1583#issuecomment-6203710183)
and [calendarless policy](https://github.com/tya5/chrona/issues/1583#issuecomment-6217533121).
This is not release acceptance: final-head CI/public counts, row2 disposition
and exact-main three-OS release remain required.

## Literal issue acceptance

### Issue #1583

- Source: [Issue #1583](https://github.com/tya5/chrona/issues/1583)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: 5wd from Monday shows Friday; actual Friday finish shows variance 0; calendar-day (`d`) items unchanged; a holiday exception before the end. | met | [Date basis tests](../../../tests/unit/chrona/presentation/model/test_working_day_date_basis.py) and [projection/table tests](../../../tests/unit/chrona/presentation/model/test_working_day_projection.py): working/civil spans, holiday/override/calendarless/signed distance controls, Friday Actual zero, Actual weekend civil closure, source-local snapshot/scenario calendars, raw dates unchanged. [Defaults tests](../../../tests/integration/test_view_defaults.py) preserve explicit calendar-days. | — |
| 2 | The #1582 CSV renders `05 Oct – 09 Oct` and `0` for `test-plan` in the default draft and `target-b`, viewed as PNG. | not met | Root viewed exact-CSV default draft PNG with05Oct–09Oct/+0d and target-b with+0d. Target-b ships no Plan column; a scratch authored View adding its existing dateRange/inclusive column also visibly shows05Oct–09Oct/+0d. [Reviewer clarification requested](https://github.com/tya5/chrona/issues/1583#issuecomment-6217961113); no silent design change or acceptance relaxation. | — |
| 3 | Public SVG/Scene changes are listed with counts in the PR. | not met | [Required public artifact gate](https://github.com/tya5/chrona/issues/1583#issuecomment-6203710183): final CI before/after artifact required; no generated public output is hand-authored. | — |

## Programme-level criteria (optional)

Architecture review: Core half-open dates remain unchanged. One source-local
typed basis and shared date helper feed canonical projection comparison facts
and pre-Layout display ranges. Scene/adapters perform no calendar arithmetic.
Calendarless presentation counts civil days without warning. Specifications06/24
and shared vocabulary express the contract; default policy is declared in YAML,
never selected by preset ID. Focused205 tests pass; schema structural/corpus/
diagnostic layers matched, but concurrent-load runtime72.1s exceeded60s and must
be rerun without raising the limit. Independent read-only review found no blocker.
