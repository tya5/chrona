<!-- chrona:literal-acceptance/v1 -->

# Issue #1296 — selected-planned window acceptance

Prepared implementation: `d0766a07ca2c50aac7044e39bd327792cef3e5c1`, adopting
ready base `4f4ee94ccc21c8d3c85021a1dc50a931d068e044` via `db0eb546`.
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

Model suite: 471 passed (25.42s). Layout allocation/natural geometry/Scene suite:
86 passed (7.85s). These are focused checks, not a full-suite claim.
After adopting #1214, window/model/render and coupled-flow tests: 22 passed
(4.47s). The subsequent bot adoption changes no product or test bytes.
Prepared WIP has no PR yet; earlier board publications retain priority.
Ordinary adoption of main `e19005d0` and published #1293/#1294/#1295 WIPs
preserves the pending formatter/axis/table migrations. Actual-default/model
and public-diagnostic tests: 17 passed (2.84s). The old test mixed default View
with Editorial Theme; it is not evidence for the current default.
Required before closure: fresh current-base corpus count table and PR checks,
automatic derived publication, and exact-main full release containing this review.
