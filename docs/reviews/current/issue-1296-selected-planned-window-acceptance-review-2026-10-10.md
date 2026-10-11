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
CI38130494419 finished with19 failed tests:8 exposed non-lane compound glyph
host closure;11 relied on earlier padding/criticality or fixture geometry.
[Published correction design/review/plan](https://github.com/tya5/chrona/issues/1296#issuecomment-6108018243)
precedes product correction `8062c71e`. Layout now closes every mark's emitted
host ID; lane IDs and strict source/slot/order validation remain authoritative.
Scene projects the same IDs, geometry and paint, without repairing associations.

Focused Python3.13 evidence:175 passed104.67s (host/point glyphs, placements,
actual Scene/SVG readable defaults);38 passed19.06s (stroke/hosted indices,
compile, project-finish invariants);67 passed6.35s (all M1 acceptance families,
host negatives and Layout/Scene structure). The adjacent fixture batch had
60 passed and one incorrect all-engineering-calendar assertion, subsequently
corrected and included in the38-test passing compile family.
Crowding and own-actual mutation tests explicitly fix their windows; colour
transport tests declare a separated rail. Their suppression, mutation, leader
paint and overlap assertions remain intact. Horizontal compression proves
newly placed labels. The default's exact new axis thinning/density warnings
and two Editorial ledger counts13→15 are asserted, not broadly waived.

Snapshot11698754531 at26337656:101 paths, none added/removed;41 of46
Scene/SVG pairs identical. The five changed pairs contain no new diagnostics:
plan-only1/47/0 primitives added/changed/removed; dependency-network0/3/0;
Editorial8/127/0; Editorial-lanes8/153/0; Title Card0/34/0. Actual SVG XML
and Scene were both inspected. Synthetic frozen-byte cases remain asserted
without normalization; removing only padding reproduces all prior hashes.
Authored examples are unchanged. Corrected-head snapshot, PR CI and exact-main
three-OS release remain required before deliberate closure.
