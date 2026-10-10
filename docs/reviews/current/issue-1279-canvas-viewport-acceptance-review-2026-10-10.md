<!-- chrona:literal-acceptance/v1 -->

# Issue #1279 — canvas viewport acceptance

Implementation `43e30d82`; source-main integration `c4f248b1` adopts
`3d363889cc8ddb42070c391edf943a44d2a1cf82` (#1285 small caps).
Its derived sync remains pending; the final ready-base snapshot and release
are not yet accepted. [PR #1311](https://github.com/tya5/chrona/pull/1311)
also carries the independent final acceptance table for #1327.
Authority: [design](../../design/issue-1279-canvas-viewport-design-2026-10-10.md)
and [implementation plan](../../planning/active/issue-1279-canvas-viewport-implementation-plan-2026-10-10.md).

## Literal issue acceptance

### Issue #1279

- Source: [issue body and negative-origin acceptance note](https://github.com/tya5/chrona/issues/1279).
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test where content needs more than the viewport yields the warning with correct sizes; a fitting surface yields none. | met | [Layout/Scene/SVG tests](../../../tests/integration/test_canvas_viewport_warning_render.py) cover both surfaces, fixed overflow and fitting content; [typed helper tests](../../../tests/unit/chrona/presentation/layout/test_canvas_viewport_warning.py) verify sizes and deterministic contributors. | — |
| 2 | On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR). | not met | [Exact-base audit](https://github.com/tya5/chrona/issues/1279#issuecomment-6094485533): all 46 SVGs byte-identical, 27 warning-only Scene changes, 19 unchanged; 27 warnings and zero membership mismatches. The PR lists every slide. This proves base `4f4ee94c`, not the subsequently advanced main; final ready-base snapshot remains required. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/commit/43e30d82) changes Layout/runtime metadata, shared reporting, tests and specifications only. No authored examples or derived output edits. | — |
| 4 | Acceptance note for this issue: a test with a *negative* viewBox origin (as in the first case) should also yield the warning, since the declared-vs-actual comparison must use the full extent, not only width/height. | met | [Real SVG tests](../../../tests/integration/test_canvas_viewport_warning_render.py) cover negative origins with fixed and auto block size; auto block has no invented height constraint. | — |

## Programme-level criteria (optional)

None; the literal acceptance and release gates control closure.

## Verification and architecture

Combined viewport, transport, completion-fixture, frame/provenance, coupled-flow,
legend and small-caps tests: **56 passed (18.27s)** on `c4f248b1`.
`tools/check_scene_primitive_delivery.py`: **32 dataclasses / 230 fields** owned.
These are focused checks, not a full-suite claim.

Independent Luna review of `8dc82f17`: no ownership or provenance loss from
small-caps integration. Layout compares the immutable original declaration
against completed full bounds and computes native-slot contributors. Scene
carries completed facts; the ledger formats their stable surface/source identity.
Warning-on/off tests preserve geometry and raw SVG in both rendering paths.
Allocation, clipping, existing network-overflow policy and project resources
are unchanged.

Exact-base audit: run `38029171845`, artifact `11661661148`, head `4f99e1a2`,
base `4f4ee94c`; 101/101 before blobs match, no paths added/retired.
ZIP SHA256 `3360dae7caad42897e6a74d8878b2d7f85e1cb10ea5268fe11ed3ca244454cd5`.
Root and independent Luna agree; all Scene changes contain only the new warning.

Closure requires final ready-base PR checks and snapshot, then successful
three-OS pytest/conformance/wheel-smoke CI on exact published main containing
this acceptance review. An old green run is not release acceptance.
