<!-- chrona:literal-acceptance/v1 -->

# Issue #1279 — canvas viewport acceptance

Implementation `43e30d82`; source-main integration `599b75ab` adopts
`f0c1a6fa` (#1289 plain zero), including #1285 small caps.
Ready base `aebf5b57c8f8a138dd5388f8d251d9fef730ea62` is adopted;
[trusted gate 38035315878](https://github.com/tya5/chrona/actions/runs/38035315878)
completed successfully. Its delta from tested ready `bf9313bb` is one review document.
The recorded snapshot below passed on its exact base; a fresh final-head snapshot,
PR checks and containing-review release remain required.
[PR #1311](https://github.com/tya5/chrona/pull/1311)
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
| 2 | On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR). | met | [Snapshot audit receipt](https://github.com/tya5/chrona/issues/1279#issuecomment-6094637076): 46 byte-identical SVGs, 27 warning-only Scenes, 19 unchanged; 27 warnings, zero membership mismatches against original declaration/full viewBox and actual Scene surface identities. Recorded artifact base is `bf9313bb`; its product/resources/outputs are byte-identical to ready `aebf5b57`. The PR lists every slide. Fresh final-head verification and release remain closure gates below. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/commit/43e30d82) changes Layout/runtime metadata, shared reporting, tests and specifications only. No authored examples or derived output edits. | — |
| 4 | Acceptance note for this issue: a test with a *negative* viewBox origin (as in the first case) should also yield the warning, since the declared-vs-actual comparison must use the full extent, not only width/height. | met | [Real SVG tests](../../../tests/integration/test_canvas_viewport_warning_render.py) cover negative origins with fixed and auto block size; auto block has no invented height constraint. | — |

## Programme-level criteria (optional)

None; the literal acceptance and release gates control closure.

## Verification and architecture

Combined viewport, transport, completion-fixture, frame/provenance, coupled-flow,
legend and small-caps tests: **56 passed (18.27s)** on `c4f248b1`.
`tools/check_scene_primitive_delivery.py`: **32 dataclasses / 230 fields** owned.
These are focused checks, not a full-suite claim.
After adopting #1289 on `599b75ab`, viewport helper/transport/render and
small-caps/plain-zero integration tests: **42 passed (19.86s)**.

Independent Luna review of `8dc82f17`: no ownership or provenance loss from
small-caps integration. Layout compares the immutable original declaration
against completed full bounds and computes native-slot contributors. Scene
carries completed facts; the ledger formats their stable surface/source identity.
Warning-on/off tests preserve geometry and raw SVG in both rendering paths.
Allocation, clipping, existing network-overflow policy and project resources
are unchanged.

Exact-base audit: run `38033996267`, artifact `11662819617`, head `dd829871`,
base `bf9313bb`; 101/101 before blobs match, no paths added/retired.
ZIP SHA256 `e606d3f533b336267a09cc6c5774ecd7b336a05a21fd10cffb9b91a30390cfb7`.
Root and independent Luna agree; all Scene changes contain only the new warning.
`bf9313bb`→`aebf5b57` changes only #1206's review document. All substantive
checks on `dd829871` passed; only derived-ready failed because main advanced.
The artifact retains its actual head/base metadata; it is not represented as
a fresh final-head artifact.

Closure requires final ready-base PR checks and snapshot, then successful
three-OS pytest/conformance/wheel-smoke CI on exact published main containing
this acceptance review. An old green run is not release acceptance.
