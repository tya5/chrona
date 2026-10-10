<!-- chrona:literal-acceptance/v1 -->

# Issue #1279 — canvas viewport acceptance

Implementation `43e30d82`; source-main integration `c4f248b1` adopts
`3d363889cc8ddb42070c391edf943a44d2a1cf82` (#1285 small caps).
Ready base `04ca067d5bef69457eb951f8601792774b16fe30` is adopted;
[trusted gate 38031344998](https://github.com/tya5/chrona/actions/runs/38031344998)
completed successfully. Its only follow-up changes are managed reports, so
the tested source and SVG/Scene trees are identical. The exact ready-base snapshot
audit passed; final PR checks and containing-review release remain pending.
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
| 2 | On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR). | met | [Exact current-base candidate audit](https://github.com/tya5/chrona/issues/1279#issuecomment-6094637076): all 46 SVGs byte-identical, 27 warning-only Scene changes, 19 unchanged; 27 warnings and zero membership mismatches against original declaration/full viewBox and actual Scene surface identities. All 101 before blobs also match ready main `04ca067d`; the PR lists every slide. Publication/release remains a closure gate below. | — |
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

Exact-base audit: run `38030343126`, artifact `11661119885`, head `09e5553d`,
base `51bc172e`; 101/101 before blobs match, no paths added/retired.
ZIP SHA256 `8aaa68fff4df940e5e3956d6c5757279c9c8ed024e2c5586eb75e16febe0ec10`.
Root and independent Luna agree; all Scene changes contain only the new warning.
Root repeated the complete artifact audit against `04ca067d`: all 101 before
blobs and authored manifests/contexts match that exact tree; the counts and list
remain unchanged. The sole `51bc172e`→`04ca067d` change is #1219's acceptance
review. Integration `a23ed349` and the final table update change reviews only,
not the audited product or resources. Artifact metadata remains its actual
`09e5553d` head; final-head PR checks are still required.

Closure requires final ready-base PR checks and snapshot, then successful
three-OS pytest/conformance/wheel-smoke CI on exact published main containing
this acceptance review. An old green run is not release acceptance.
