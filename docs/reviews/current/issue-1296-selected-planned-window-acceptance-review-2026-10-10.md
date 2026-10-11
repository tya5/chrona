<!-- chrona:literal-acceptance/v1 -->

# Issue #1296 — selected-planned window acceptance

Padding implementation: `d0766a07ca2c50aac7044e39bd327792cef3e5c1`;
integration correction: pre-code Spec06 publication `f797c2c1` and
[architecture/implementation decision](https://github.com/tya5/chrona/issues/1296#issuecomment-6105416153).
Authority: [current design and plan](https://github.com/tya5/chrona/issues/1296#issuecomment-6094171095).
Independent architecture/code review found no layer breach. View owns padding;
Core marks, explicit windows and selected-comparison behavior are unchanged.

## Literal issue acceptance

### Issue #1296

- Source: [Issue #1296](https://github.com/tya5/chrona/issues/1296)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Tests: a single span, a single gate, and two gates on the same date each render with the default preset. From the Scene, every object's label is placed (no suppression) and the window strictly contains every mark. | met | [Actual library-default Scene/SVG cases](../../../tests/integration/test_selected_planned_minimum_window.py) resolve all four default resources, including a one-day span and issue dates/titles; labels emitted, marks strictly inside plot and padded dates verified. | — |
| 2 | A projection that is still degenerate yields a diagnostic whose message names the window dates and the selected object ids. | met | [Public render/report fault-injection test](../../../tests/integration/test_selected_planned_minimum_window.py) verifies the real diagnostic message, source path, dates/IDs/cause and absence of generic fallback; [Layout/Date boundaries](../../../tests/unit/chrona/presentation/model/test_selected_planned_window.py) cover model invariants. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/commit/d0766a07ca2c50aac7044e39bd327792cef3e5c1) contains only View projection, Layout validation, Spec06 and synthetic tests. | — |

## Programme-level criteria (optional)

None. Local criteria do not substitute for the required release gate.

## Verification and release

Publication: [M1 integration PR1416](https://github.com/tya5/chrona/pull/1416).
[Published correction design/review/plan](https://github.com/tya5/chrona/issues/1296#issuecomment-6108018243)
precedes product correction `8062c71e`. Layout now closes every mark's emitted
host ID; lane IDs and strict source/slot/order validation remain authoritative.
Scene projects the same IDs, geometry and paint, without repairing associations.

Focused Python3.13 evidence:175 passed104.67s (host/point glyphs, placements,
actual Scene/SVG defaults);38 passed19.06s (stroke/hosted indices, compile,
project-finish);67 passed6.35s (M1 acceptance and structure). On READY7563df4c,
the full affected CLI/gallery and schedule-unit batch passed126 tests350.33s.
Synthetic crowding/mutation/paint fixtures declare explicit windows or rails;
their safety assertions remain. Exact default warning and ledger deltas are
asserted, not broadly waived.

Corrected-head snapshot11700046472 atd98ca1be:101 paths, none added/removed;41 of46
Scene/SVG pairs identical. The five changed pairs contain no new diagnostics:
plan-only1/47/0 primitives added/changed/removed; dependency-network0/3/0;
Editorial8/127/0; Editorial-lanes8/153/0; Title Card0/34/0. Actual SVG XML
and Scene were both inspected; all46 Scene/SVG pairs match the preceding26337656
snapshot. Synthetic frozen-byte cases remain asserted without normalization.
Current-head CI38132741366 passed all product/reproduction checks; derived-ready
failed only because main advanced. Post1413 integrationc783dc73 passes57 focused
tests16.75s (HALCYON/compile, project-finish/units, sparse Scene/SVG and headings).
Exact trusted READYcc94cf2c is adopted without conflicts or product/test changes.
Fresh current-head snapshot/checks and exact-main three-OS release remain
required before closure.
