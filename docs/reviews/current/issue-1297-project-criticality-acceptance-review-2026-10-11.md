<!-- chrona:literal-acceptance/v1 -->

# Project criticality acceptance (#1297)

[Current design, architecture and implementation record](https://github.com/tya5/chrona/issues/1297#issuecomment-6094837156). Authority: Specs04/57/66, published before product code in `ea05445e`; implementation `2ef6a80d`.

## Literal issue acceptance

### Issue #1297

- Source: [Issue #1297](https://github.com/tya5/chrona/issues/1297)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A scheduler test with the repro above. `survey` has float equal to the working days between its finish and the project finish. `campaign` is not critical. `build` keeps its float to the fixed `launch` (21 working days). | met | [CPM fixture](../../../tests/unit/chrona/scheduling/test_project_finish_analysis.py) independently counts survey13 weekdays, asserts build21 and excludes the unrelated fixed chain. | — |
| 2 | A test that every object listed in `criticalObjectIds` has zero float and lies on a dependency path to the project finish (the rule, checked over every conformance fixture). | met | [Conformance invariant](../../../tests/unit/chrona/scheduling/test_project_finish_analysis.py) enumerates all six conformance Projects and checks zero float/reachability, with the embedded delivery oracle excluded from its Project mapping. | — |
| 3 | A test that the emitted unit field matches Spec 57 for a calendar-day object and a working-day object. | met | [Serialization/basis tests](../../../tests/unit/chrona/scheduling/test_project_finish_analysis.py) and [public unit schema](../../../tests/unit/chrona/app/test_schedule_float_contract.py) cover both bases, calendar fallback/override and invalid or ambiguous records. | — |
| 4 | Spec 57, Spec 66 and the MCP description state the same unit (checked by a doc test or the existing doc check). | met | [Authority agreement test](../../../tests/unit/chrona/app/test_schedule_float_contract.py) checks both unit names and `{value, unit, calendar}` in Specs57/66, agent guide and actual tool description. | — |
| 5 | Do not edit `examples/**`. | met | [Product commit](https://github.com/tya5/chrona/commit/2ef6a80d) changes code, specifications and synthetic tests only; final authored `git diff --name-only origin/main...HEAD -- examples` is empty. | — |

## Programme-level criteria (optional)

Release pending: final READY integration, completed public Scene/SVG audit with every critical-role change disclosed, current-head PR gates and acceptance-containing exact-main three-OS release. No closure is authorized by local rows.

After ordinary `9ee4dbce` adoption, CLI assertions3, schedule characterization23 and explicit-unit contracts10 pass. Scheduler/hash-seed batch23 passes (56.60s), including eight seeds per command. Broader scheduler, point/calendar/property, usecase, projection and MCP consumers:322 passed (61.20s). Only four successful schedule golden records change; baseline/current raw comparison proves placements, diagnostics, warnings, files and exit codes unchanged. HALCYON's longer unit-bearing stdout uses the existing stream digest policy. The public audit remains pending.

## Architecture conclusion

Scheduler owns one project finish, frozen fixed/anchored latest dates, zero-float driving-path closure and effective calendar basis. Projection explicitly takes the numeric value; CLI/MCP serialize typed facts, with no legacy scalar alias. View/Theme/Layout/Scene/adapters neither reanalyze criticality nor move dates. CLI Project ordering remains deterministic and dev B's merged warning-location and adapter fixes are retained.
