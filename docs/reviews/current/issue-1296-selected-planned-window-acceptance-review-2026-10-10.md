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

Current integration adopts corrected public table `f02bc0bb` and trusted READY main
`477e571d` by ordinary merge without conflicts. Own-worktree Python3.13:
43 focused tests pass in two batches (17 in3.56s;26 in1.03s), covering
selected-planned Scene/SVG and diagnostics, model window modes and shared
visibility validation after the bounded-heading/closed-metric correction.
Earlier own-worktree Python3.11:141 tests pass (133.82s), covering actual default
Scene/SVG/degenerate diagnostic, selected-planned model, missing-Actual scope,
lane inventory, bounded packaged tables, explicit windows, date/axis,
merged legend-grid, live ID-site/ownership/schema-annotation checks.
The comparison fixture keeps explicit zero-margin/whole-projection assertions;
the shared window validator rejects before visibility geometry with dates/IDs/cause.

CLI migration remains three stdout records only (axis density and the disclosed
six-label suppression inventory); argv/exit/stderr/file metadata unchanged.
Own Python3.11 CLI characterization previously4 passed; Python3.13's
pre-existing unknown-command wording failure is not re-recorded or excluded.

Public preparation does not authorize acceptance. No active PR or authored
examples changes. After predecessor #1295 merges: reconcile latest READY,
inspect current schema/PR/corpus Scene-SVG evidence and the exact
acceptance-containing main three-OS gate before deliberate closure.
