<!-- chrona:literal-acceptance/v1 -->

# Issue 1701 — hierarchy acceptance

Row1 candidate: `c0e78982c`, following published [plan6246724848](https://github.com/tya5/chrona/issues/1701#issuecomment-6246724848).
View projection closes ordinary/folded primary occurrences into typed display
ranges; each source retains its date basis, and nested ranges close once.
Comparison subjects keep their own dates. Layout geometry, Scene/adapters,
Scheduler dates and dependency declarations are unchanged. Independent review
confirms consistency with Spec06's display/Core boundary. Row1 changes no presets.

Focused command: `.venv/bin/python -m pytest -q tests/unit/chrona/presentation/model/test_date_range_display.py tests/unit/chrona/presentation/model/test_working_day_date_basis.py tests/integration/test_group_rollup_display_range.py --tb=short`.
The broader dates/projection/forecast/grouping/native batch passed132 tests.
Integration `163ba8725` with the independently reviewed legend correction on
ready main `381cf404a` passes64 combined date/legend/native tests.
The native regression fails before the correction and passes afterward;
work-calendar, tied/late point, folded membership, nested and comparison cases
are covered. Official PR artifact and exact-main full release remain pending.
This is focused evidence, not release acceptance.

Row2 design/architecture review `f4475ec01` and plan `939a80285` preceded code,
after [reviewer approval6247026872](https://github.com/tya5/chrona/issues/1701#issuecomment-6247026872).
Specs06/38/50 own the selected contract. Source closure `62fa2895d`, admission/
Layout `ad30b5aaf`, preset declarations `d27e086d9` and correction `1ca25a3e0`
keep names source-local through ordinary, lane, attached, folded and key-row
paths. Attached composites use the same canonical source/container key; point
policies admit a name regardless of title/path source. Style identities,
selection, grouping, scheduling and Scene/adapter ownership remain unchanged.

The native18-test batch at `3cbe20911` includes every15 preset, explicit bound/
unbound-role checks and an honest full-window suppression negative.
[All15 PNG/SVG/Scene witnesses and synthetic inputs](https://github.com/tya5/chrona/tree/cfb05a1eb28ac10a0b1b30fb6588ad1c451832e9/review-evidence/issue-1701)
are public; root inspected every PNG. SVG checks join actual text/tspan content,
not Scene-only names. Header coverage leaves inner names without repeating the
represented ancestor; table-less and intentionally ungrouped presets retain
full paths. Existing fit policies and diagnostics are not waived.
Point/path/style159, composite152 and preset/closure62 focused tests pass
(overlapping); schema equivalence preserves all five invalid baseline verdicts.
The final combined PR artifact and exact-main full release are still required.
Ready-base integration `5a2acd12a` follows `a27a86cd3` (902 item2 and B1709 merged).
Final correction `3abc8479d` passes197 focused presentation/native/schema tests;
preset/schema89 passes (overlapping). The scoped legacy fixture updates retain
the exact source-name rule and independently authored reference Views; two chip
Scene hash changes are proven View-provenance-only with identical SVG bytes.
Schema equivalence retains
one additive/one delta/40 equal and the same five invalid baseline documents.
Import-direction and literal-review checks pass. Independent final review found
no source-locality, header-coverage or dev-B selection/summary boundary gap.

## Literal issue acceptance

### Issue #1701

- Source: [Issue #1701](https://github.com/tya5/chrona/issues/1701)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a group with a child gate after its last span shows a range ending on the gate date. | met | [Native Scene/SVG regression](../../../tests/integration/test_group_rollup_display_range.py) renders `01 Mar – 06 Mar`, while canonical group end remains Mar6 and dependency declarations remain unchanged. [Model tests](../../../tests/unit/chrona/presentation/model/test_date_range_display.py) also cover a point strictly after the exclusive span endpoint. Release proof pending above. | — |
| 2 | Design record for nested grouping (levels, header depth, folding, how presets declare it), reviewed before code; then a synthetic 3-level twin rendered by the bundled presets with no level lost. | met | [Published-before-code design/plan](../../planning/active/issue-1701-hierarchy-work-record-2026-10-18.md), reviewer approval above, [native all-preset tests](../../../tests/integration/test_hierarchy_preset_names.py) and public15 PNG/SVG/Scene witnesses above. Root verified all three names in actual native output; focused only, release proof pending. | — |

## Programme-level criteria (optional)

The issue remains open until the combined PR artifact and required exact-main
three-OS full release containing both literal rows complete successfully.
