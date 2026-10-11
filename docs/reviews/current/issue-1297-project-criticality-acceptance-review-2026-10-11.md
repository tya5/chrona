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

Release pending: final READY integration, current-head PR snapshot/gates and acceptance-containing exact-main three-OS release. No closure is authorized by local rows.

Current PR1416 correction `8062c71e` updates consumers to the approved rule:
compiled HALCYON and its synthetic twin have no zero-float driving path to
project finish; typed bus-test float is41 working-days of engineering. Placement,
lag and twin-equality assertions remain. Complete compile/stroke/hosted-index/
project-finish family38 PASS19.06s; combined M1 acceptance/structure67 PASS6.35s.
On READY7563df4c, the affected CLI/gallery and schedule-unit batch passed126
tests350.33s. Four successful schedule golden records change only typed float
facts; placements, diagnostics, warnings, files and exit codes are unchanged.
HALCYON's longer unit-bearing stdout uses the existing stream digest policy.

Corrected-head snapshot11700046472 atd98ca1be: all46 Scene/SVG pairs parse;
the criticality-only change is `halcyon-1/dependency-network`. Its existing
`frr-launch`, `launch-leop`, `leop-firstlight` edges lose critical-role paint
because the old component/fixed-date inference is not a zero-float driving
path to project finish. Added/removed primitives, changed coordinates/routes,
text and diagnostics:0. Changed primitive roles/paints:3; the manifest role
counts follow those changes. SVG XML comparison independently confirms only
the same three `data-purpose`/`stroke` attributes change; element counts and
all text remain unchanged. Expected evidence mismatch is disclosed, not
absorbed into authored examples. Other M1 deltas are disclosed in the1296/1347
reviews. CI38132741366 passed all product/reproduction checks; derived-ready
failed only because main advanced. Final post1413 READY integration, its fresh
snapshot/checks and exact-main three-OS release remain required before closure.

## Architecture conclusion

Scheduler owns one project finish, frozen fixed/anchored latest dates, zero-float driving-path closure and effective calendar basis. Projection explicitly takes the numeric value; CLI/MCP serialize typed facts, with no legacy scalar alias. View/Theme/Layout/Scene/adapters neither reanalyze criticality nor move dates. CLI Project ordering remains deterministic and dev B's merged warning-location and adapter fixes are retained.
