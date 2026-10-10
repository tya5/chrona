<!-- chrona:literal-acceptance/v1 -->

# Issue #1279 — canvas viewport acceptance

Implementation: `43e30d82`, prepared by ordinary merge `940cf434` on ready main
`484f5cd83ac24e91b7d435be18dfb5be1ebade04`. Current viewport integration,
Layout and transport tests: 26 passed (7.00s). This preparation is not yet the
published PR head. The current 71-slide audit and exact-main release remain
pending behind M0; do not close.
Authority: [design](../../design/issue-1279-canvas-viewport-design-2026-10-10.md)
and [implementation plan](../../planning/active/issue-1279-canvas-viewport-implementation-plan-2026-10-10.md).

## Literal issue acceptance

### Issue #1279

- Source: [Issue #1279](https://github.com/tya5/chrona/issues/1279)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test where content needs more than the viewport yields the warning with correct sizes; a fitting surface yields none. | met | [Real Layout/Scene/SVG tests](../../../tests/integration/test_canvas_viewport_warning_render.py) cover fixed overflow, fitting content and both surfaces; [typed helper tests](../../../tests/unit/chrona/presentation/layout/test_canvas_viewport_warning.py) verify full-edge sizes and deterministic contributors. | — |
| 2 | On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR). | not met | [Predecessor public-materializer batch](#public-materializer-batch): 70/70 checked, 49 warnings / 21 fitting surfaces. This excludes the new Sunday slide; a fresh 71-slide snapshot audit and updated PR list are required. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/commit/43e30d82) changes Layout/runtime metadata, the shared report, tests and specifications only; no authored examples or derived paths. | — |
| 4 | Acceptance note for this issue: a test with a *negative* viewBox origin (as in the first case) should also yield the warning, since the declared-vs-actual comparison must use the full extent, not only width/height. | met | [Real SVG negative-origin tests](../../../tests/integration/test_canvas_viewport_warning_render.py) cover fixed and auto block; auto block has no invented height constraint. | — |

## Programme-level criteria (optional)

None; the literal acceptance and release gates control closure.

## Evidence and architecture

Focused batch: 152 passed (23.67s). Expanded both-surface geometry/transport
batch: 11 passed (7.61s). Independent frame, texture, overlay, PNG and auto-block
regressions: 83 passed (17.34s). Latest-main #918/#1279 integration: 19 passed
(9.94s). These overlapping focused runs are not a full-suite claim.
PR #1311 run 37976489537 found two stale `SimpleNamespace` completion fixtures
missing the typed request's optional `declared_viewport` field. Both now declare
`None`; no production fallback or contract change. The two fixture files plus
viewport render/transport tests pass together: 23 passed (7.16s). The superseded
red run is not release evidence; replacement exact-head CI remains required.
Replacement run 37979100227 passes all source checks; only derived-ready fails
because its old base advanced. [Fresh artifact audit](https://github.com/tya5/chrona/pull/1311#issuecomment-6088023784)
proves 70 unchanged SVGs, 21 unchanged Scenes and 49 warning-only Scene changes.
After merging ready `0617e671`, the viewport, stale-fixture, provenance and
figure-label suites pass together: 36 passed (15.23s). Fresh exact-head gates
remain required; no product-policy correction was needed.
Scene delivery registry: 31 dataclasses / 226 fields have explicit owners.

Independent review found no ownership breach: Layout compares the immutable
original declaration after canvas completion; Scene carries completed facts;
the shared ledger formats one stable surface/source identity. Geometry,
allocation, clipping and the existing network allocation warning are unchanged.
Warning-on/off tests preserve primitives, slots, rows, groups, canvas and SVG
bytes in both rendering paths. No Project-specific rule or resource migration.

## Public-materializer batch

Predecessor evidence only: this 70-slide batch does not prove current-main
acceptance after the Sunday slide was added.

One batch of 70 `materialize(manifest, slide, temporary_output, write=False)`
calls used four workers and the worktree's Python 3.11 venv. Existing SVG bytes
matched in all 70 calls. For Scene comparison only, the process-local serializer
removed diagnostics with the new canvas-warning code; all remaining Scene bytes
matched in all 70 calls. The actual returned Scene and warning records retained
the new warning. No source or expected-output files were patched by that check.

Each declared viewport was read from its manifest/context closure and compared
with the actual SVG full viewBox. Runtime warning membership matched exactly:
controller-z 40, controller-z-ja 2, halcyon-1 6, orion-asic 1; 21 fitting slides
had none. All corpus surfaces are table-timeline; synthetic tests independently
cover dependency-network. Ready main's sole follow-up generated change is the
diagnostic inventory, so the checked SVG/Scene baseline is unchanged.

Reproducible focused command: `.venv/bin/python -m pytest -q
tests/integration/test_canvas_viewport_warning_render.py
tests/unit/chrona/usecases/test_canvas_viewport_warning_transport.py` (11 passed).
Delivery command: `.venv/bin/python tools/check_scene_primitive_delivery.py`.

Required release evidence: exact-head PR checks and generated snapshot audit,
then automatic exact-main three-OS pytest/conformance/wheel smoke. Neither a
focused pass nor an old green run satisfies that gate.
