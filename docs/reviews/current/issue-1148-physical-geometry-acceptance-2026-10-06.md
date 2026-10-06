<!-- chrona:literal-acceptance/v1 -->

# Issue #1148 — acceptance review

Source: [#1148](https://github.com/tya5/chrona/issues/1148), observed 2026-10-06.
Design/plan authority: the issue's [living Status](https://github.com/tya5/chrona/issues/1148#issuecomment-6010708341), Spec 07 and Spec 08.
Published implementation: [PR #1185](https://github.com/tya5/chrona/pull/1185), source `cfea0a79`, ready publication `61d1fb74`; review baseline `7b8051ca` includes #1149. Synthetic rows are met; the reviewer [explicitly deferred adoption](https://github.com/tya5/chrona/issues/1148#issuecomment-6016572407) to its migration PR, outside the dev closing gate. Close only after the three-OS release run on the exact main commit publishing this review succeeds; cite that run in the closing comment.

## Literal issue acceptance

### Issue #1148

- Source: [Issue #1148](https://github.com/tya5/chrona/issues/1148)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Changing a mark's or chip's height leaves a px-declared radius unchanged in the Scene. | met | [Synthetic height changes and validated public Scene JSON](../../../tests/integration/test_physical_corner_radius_render.py). | — |
| 2 | `capsule` gives exactly half the shorter side. | met | [Public Scene assertion](../../../tests/integration/test_physical_corner_radius_render.py); [geometry invariants](../../../tests/unit/chrona/presentation/layout/test_issue_1148_physical_radius_geometry.py). | — |
| 3 | `strokeAlign: inside` keeps the stroke's outer edge on the declared bounds. | met | [Authored Theme → Layout → Scene → actual SVG pixels](../../../tests/integration/test_stroke_alignment_render.py); [curved compound contours and holes](../../../tests/unit/chrona/presentation/renderers/test_issue_1148_stroke_clip_adapters.py). | — |
| 4 | A derived attachment puts the terminal tip on the port. | met | [Completed reference and actual head-only SVG pixels](../../../tests/unit/chrona/presentation/layout/test_derived_terminal_attachment.py); [public Scene schema](../../../tests/integration/test_derived_terminal_render.py). | — |
| 5 | Absent declarations give byte-identical output. | met | [Final-head CI](https://github.com/tya5/chrona/actions/runs/37443289593), artifact11402153312, head3319c30a/base184f8c34: all65 SVG and65 Scene files byte-identical;139 paths, no additions/retirements. Baseline Git blobs and ready-main outputs independently verified. Only diagnostic inventory and optional vocabulary coverage change. [Synthetic absent/center](../../../tests/integration/test_stroke_alignment_render.py) also matches. | — |
| 6 | Target B migrates to px radii. | deferred | [Reviewer-approved disposition](https://github.com/tya5/chrona/issues/1148#issuecomment-6016572407): adoption is the reviewer's step, not a dev closing condition; no claim that migration already happened. | [Reviewer-owned migration tracking](https://github.com/tya5/chrona/issues/1148#issuecomment-6016572407); its post-review supplies the migration PR. |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and architecture

[Final-head PR CI](https://github.com/tya5/chrona/actions/runs/37443289593) passed all pytest shards, conformance, MCP, newest-Python reproduction and derived-ready. [Exact-main three-OS release](https://github.com/tya5/chrona/actions/runs/37448394730) passed on `61d1fb74`: Ubuntu/macOS/Windows pytest, conformance and wheel smoke, MCP and newest-Python public materializers. This earlier implementation release does not replace the exact-main gate for publishing this updated review.

Schema equivalence: 523 documents, 423 mapped, 739 probes; four pre-existing invalid fixtures unchanged. Focused and synthetic command evidence is in the [living Status](https://github.com/tya5/chrona/issues/1148#issuecomment-6010708341). No generated files or reviewer YAML were authored.

Theme references resolve before Layout. Layout completes radii, text clearance, terminal attachment/run and closed contour clips, including lane/multipart identities and network nodes. Scene projects the typed closure; SVG serializes it without contour scaling or closure inference, and unsupported typeset adapters explicitly refuse aligned strokes. No unresolved implementation or architecture finding remains; reviewer migration is the approved separate successor.
