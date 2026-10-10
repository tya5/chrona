<!-- chrona:literal-acceptance/v1 -->

# Issue #1279 — canvas viewport acceptance

Implementation `43e30d82`; source-main integration `599b75ab` adopts
`f0c1a6fa` (#1289 plain zero), including #1285 small caps.
Ready base `b1c65cd521fca5a538ccc9863ec355637fe275c2` is adopted;
[trusted gate 38036901541](https://github.com/tya5/chrona/actions/runs/38036901541)
completed successfully. Integration `d33cc28d` adopts #1282 band-pattern admission;
86 combined band-pattern/group-tab/viewport tests pass (14.00s).
The source-to-ready delta changes only the generated diagnostic inventory.
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
| 2 | On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR). | met | [Snapshot audit receipt](https://github.com/tya5/chrona/issues/1279#issuecomment-6094637076): 46 byte-identical SVGs, 27 warning-only Scenes, 19 unchanged; 27 warnings, zero membership mismatches against original declaration/full viewBox and actual Scene surface identities. Recorded artifact base is `aebf5b57`; authored resources and generated Scene/SVG bytes are unchanged at ready `b1c65cd5`. The PR lists every slide. The new band-pattern capability is opt-in and covered by the integration batch; fresh final-head verification and release remain closure gates below. | — |
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

Exact-base audit: run `38035859826`, artifact `11663781660`, head `c44f991d`,
base `aebf5b57`; 101/101 before blobs match, no paths added/retired.
ZIP SHA256 `4034e3125be5514b4e587f9c04cca36a5fc302d76fe4ff4ae5bce6c0861d85d1`.
Root and independent Luna agree; all Scene changes contain only the new warning.
All substantive checks on `c44f991d` passed; only derived-ready failed because
main advanced to #1282. Source integration adds no authored resource or Scene/SVG edits.
The artifact retains its actual head/base metadata; it is not represented as
a fresh final-head artifact.

Closure requires final ready-base PR checks and snapshot, then successful
three-OS pytest/conformance/wheel-smoke CI on exact published main containing
this acceptance review. An old green run is not release acceptance.
