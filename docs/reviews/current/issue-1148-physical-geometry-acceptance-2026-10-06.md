<!-- chrona:literal-acceptance/v1 -->

# Issue #1148 — candidate acceptance

Source: [#1148](https://github.com/tya5/chrona/issues/1148), observed 2026-10-06.
Design/plan authority: the issue's [living Status](https://github.com/tya5/chrona/issues/1148#issuecomment-6010708341), Spec 07 and Spec 08.
Candidate: `4851fdb6`, including main source `9e117b73`; published WIP before reconciliation: `6f2f4a4d`.
**Not release-accepted.** Implementation PR, corpus byte comparison, Target B adoption and exact-main three-OS evidence are pending.

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
| 5 | Absent declarations give byte-identical output. | not met | [Synthetic absent/center SVG and Scene surfaces](../../../tests/integration/test_stroke_alignment_render.py) match; full public materializer byte comparison awaits the single implementation-PR snapshot. | — |
| 6 | Target B migrates to px radii. | not met | Reviewer adoption [requested](https://github.com/tya5/chrona/issues/1148#issuecomment-6011662434); current Target B still uses hand-converted ratios/em. | — |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and architecture

On candidate `4851fdb6`: the following post-#1184 batch passed **150 tests**; final alignment integration passed **9 tests** (overlapping counts).

```sh
.venv/bin/python -m pytest -q tests/unit/chrona/presentation/model/test_theme_references.py tests/unit/chrona/presentation/layout/test_stroke_alignment.py tests/unit/chrona/presentation/layout/test_derived_terminal_attachment.py tests/unit/chrona/presentation/layout/test_dependency_network.py tests/unit/chrona/presentation/renderers/test_issue_1148_stroke_clip_adapters.py tests/integration/test_physical_corner_radius_render.py tests/integration/test_stroke_alignment_render.py tests/integration/test_derived_terminal_render.py
.venv/bin/python -m pytest -q tests/integration/test_stroke_alignment_render.py
.venv/bin/python -m tools.schema_equivalence --base-rev origin/main
```

Schema equivalence passed against `9e117b73`: 523 tracked documents, 423 mapped, 739 probes; four pre-existing invalid fixtures unchanged. No generated files or reviewer YAML were authored.
Theme references resolve before Layout. Layout completes radii, text clearance, terminal attachment/run and closed contour clips, including lane/multipart identities and network nodes. Scene projects the typed closure; SVG serializes it without contour scaling or closure inference, and unsupported typeset adapters explicitly refuse aligned strokes. Synthetic center output remains unchanged. Release remains open until rows 5–6 and exact published-main CI are verified.
