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

Combined predecessor integration `73552416` includes #1292/#1293/#1295,
final #1294 repair `ac14998c` and main `b65df355`. Its new early visibility
entry exposed a missing diagnostic detail; the failing public test was retained.
One Layout projection-window validator now runs before early/direct/candidate
geometry. It keeps the existing code/path and dates/selected IDs/cause;
normal model padding and completed geometry remain unchanged.

Focused combined suite:90 passed (62.41s): actual library-default Scene/SVG,
public fault-injection diagnostic, model windows, explicit clipping, inclusive
date display, bounded tables and default-axis windows. Nine parameterized
early/direct/candidate cases cover equal, reversed and invalid bounds and
prove no visibility geometry is built before rejection. Structural checks:
11 packages/37 inward edges;228 modules reachable, none orphaned.

No active PR or full-release claim. Main `b65df355` is still synchronizing;
predecessor merges and final trusted READY adoption remain required. Before
closure, inspect the fresh corpus count table/Scene/SVG, current-head PR gates
and review-containing exact-main three-OS release. No authored examples edits.
