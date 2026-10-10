<!-- chrona:literal-acceptance/v1 -->

# Issue #1296 — selected-planned window acceptance

Prepared implementation: `d0766a07ca2c50aac7044e39bd327792cef3e5c1`, base `8388f8158da881a3bb1c2d93f0b175a7e3cc0a07`.
Authority: [current design and plan](https://github.com/tya5/chrona/issues/1296#issuecomment-6094171095).
Independent architecture/code review found no layer breach. View owns padding;
Core marks, explicit windows and selected-comparison behavior are unchanged.

## Literal issue acceptance

### Issue #1296

- Source: [Issue #1296](https://github.com/tya5/chrona/issues/1296)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Tests: a single span, a single gate, and two gates on the same date each render with the default preset. From the Scene, every object's label is placed (no suppression) and the window strictly contains every mark. | met | [Four synthetic Editorial-default Scene/SVG cases](../../../tests/integration/test_selected_planned_minimum_window.py), including a one-day span: 4 passed (2.64s); labels emitted, marks strictly inside the plot and padded dates verified. | — |
| 2 | A projection that is still degenerate yields a diagnostic whose message names the window dates and the selected object ids. | met | [Owner-local Layout and Date-boundary tests](../../../tests/unit/chrona/presentation/model/test_selected_planned_window.py) assert dates, selected IDs and cause; existing projection model suite passes. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/commit/d0766a07ca2c50aac7044e39bd327792cef3e5c1) contains only View projection, Layout validation, Spec06 and synthetic tests. | — |

## Programme-level criteria (optional)

None. Local criteria do not substitute for the required release gate.

## Verification and release

Model suite: 471 passed (25.42s). Layout allocation/natural geometry/Scene suite:
86 passed (7.85s). These are focused checks, not a full-suite claim.
Prepared WIP has no PR yet; earlier board publications retain priority.
Required before closure: fresh current-base corpus count table and PR checks,
automatic derived publication, and exact-main full release containing this review.
