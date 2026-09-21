# Issue #46 revised implementation plan

1. Replace simplified View additions with the accepted labels, axis, markers, shading, and annotation-object contracts; retain legacy inputs.
2. Build explicit multi-level axis/ticks, as-of markers, calendar/range shading, plot/table labels, and numbered anchor indices from normalized View data.
3. Extend Summary Profile with target list metrics and `figures`, preserving legacy line panels.
4. Bind all required semantic HALCYON theme roles and update HALCYON Views/Project/Summary resources to exercise the contracts.
5. Materialize all three declared contexts through the public CLI, publish SVG evidence, add focused regression coverage, and delegate full `pytest`.

Every phase is published before the next one starts.