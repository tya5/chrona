<!-- chrona:literal-acceptance/v1 -->

# Issue 1701 — hierarchy acceptance

Row1 candidate: `c0e78982c`, following published [plan6246724848](https://github.com/tya5/chrona/issues/1701#issuecomment-6246724848).
View projection closes ordinary/folded primary occurrences into typed display
ranges; each source retains its date basis, and nested ranges close once.
Comparison subjects keep their own dates. Layout geometry, Scene/adapters,
Scheduler dates and dependency declarations are unchanged. Independent review
confirms consistency with Spec06's display/Core boundary. No preset edits.

Focused command: `.venv/bin/python -m pytest -q tests/unit/chrona/presentation/model/test_date_range_display.py tests/unit/chrona/presentation/model/test_working_day_date_basis.py tests/integration/test_group_rollup_display_range.py --tb=short`.
The broader dates/projection/forecast/grouping/native batch passed132 tests.
Integration `163ba8725` with the independently reviewed legend correction on
ready main `381cf404a` passes64 combined date/legend/native tests.
The native regression fails before the correction and passes afterward;
work-calendar, tied/late point, folded membership, nested and comparison cases
are covered. Official PR artifact and exact-main full release remain pending.
This is WIP evidence, not issue or release acceptance.

## Literal issue acceptance

### Issue #1701

- Source: [Issue #1701](https://github.com/tya5/chrona/issues/1701)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a group with a child gate after its last span shows a range ending on the gate date. | met | [Native Scene/SVG regression](../../../tests/integration/test_group_rollup_display_range.py) renders `01 Mar – 06 Mar`, while canonical group end remains Mar6 and dependency declarations remain unchanged. [Model tests](../../../tests/unit/chrona/presentation/model/test_date_range_display.py) also cover a point strictly after the exclusive span endpoint. Release proof pending above. | — |
| 2 | Design record for nested grouping (levels, header depth, folding, how presets declare it), reviewed before code; then a synthetic 3-level twin rendered by the bundled presets with no level lost. | not met | [Read-only preflight](https://github.com/tya5/chrona/issues/1701#issuecomment-6245837907) identifies the remaining topology/capability boundary; full nested-grouping design and implementation are not part of row1. Existing headers/preset grouping semantics are unchanged. | — |

## Programme-level criteria (optional)

The issue remains open until row2 and the required release evidence are complete.
