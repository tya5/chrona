<!-- chrona:literal-acceptance/v1 -->

# Issue 1701 — hierarchy acceptance

Implementation is merged in PR1712 at `3d915fbc9`; exact-main
`96bdfbb7cc2869782905dbc7626ddfdc03f2ef5f` passed native three-OS full release
[39119120797](https://github.com/tya5/chrona/actions/runs/39119120797): Linux
13,563, macOS 13,568, and Windows 13,560 tests passed, as did conformance,
platform probes, wheel build/smoke, newest-Python public reproduction, and the
MCP floor. Design `f4475ec01`, plan
`939a80285`, and reviewer approval [6247026872](https://github.com/tya5/chrona/issues/1701#issuecomment-6247026872)
preceded code. Focused tests prove both criteria, including all bundled presets.
The [public 15-preset PNG/SVG/Scene evidence](https://github.com/tya5/chrona/tree/cfb05a1eb28ac10a0b1b30fb6588ad1c451832e9/review-evidence/issue-1701)
was inspected; actual names are present in rendered output. Both literal
criteria and exact-main release gates are met; issue #1701 is closed.

Boundary review: Model owns source-local ancestry and display ranges; Layout
consumes typed name facts with the existing text placement/fit rules. Scene
and adapters receive completed placements. Core dates/relations and View
selection/packing are unchanged, consistent with Specs06/38/50. The
[shared PR/artifact review](issue-1703-legend-acceptance-review-2026-10-18.md)
is complete; its custom public Views do not substitute for the separate
all-preset native witnesses above.

## Literal issue acceptance

### Issue #1701

- Source: [Issue #1701](https://github.com/tya5/chrona/issues/1701)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a group with a child gate after its last span shows a range ending on the gate date. | met | [Native Scene/SVG regression](../../../tests/integration/test_group_rollup_display_range.py) renders `01 Mar – 06 Mar`, while canonical group end remains Mar6 and dependency declarations remain unchanged. [Model tests](../../../tests/unit/chrona/presentation/model/test_date_range_display.py) also cover a point strictly after the exclusive span endpoint. | — |
| 2 | Design record for nested grouping (levels, header depth, folding, how presets declare it), reviewed before code; then a synthetic 3-level twin rendered by the bundled presets with no level lost. | met | [Published-before-code design/plan](../planning/issue-1701-hierarchy-work-record-2026-10-18.md), reviewer approval above, [native all-preset tests](../../../tests/integration/test_hierarchy_preset_names.py) and public15-preset PNG/SVG/Scene witnesses above. | — |

## Programme-level criteria (optional)

Both literal criteria and the exact-main release gate are met; issue #1701 is
closed.
