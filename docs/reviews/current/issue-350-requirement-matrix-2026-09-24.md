# #350 Requirement Matrix

| Requirement | Direct evidence | Status |
| --- | --- | --- |
| R350-01 normalization | `tests/unit/chrona/presentation/icons/test_normalizer.py`, `test_importer.py` | accepted |
| R350-02 stroke paths | `test_icon_svg.py::test_svg_serializes_completed_stroke_icon_path_with_layout_scale` | accepted |
| R350-03 catalog sets | `tests/unit/chrona/presentation/contracts/test_icon_catalog.py`, closure tests | accepted |
| R350-04 import/default | importer tests; packaged-resource contract test | accepted |
| R350-05 reachable targets | `tests/unit/chrona/presentation/layout/test_visual_targets.py`; render target inventory | accepted |
| R350-06 target vocabulary | `tests/integration/test_render.py` target-family fixtures | accepted |
| R350-07 sides/reservation | plot, variance, annotation integration fixtures | accepted |
| R350-08 ratios/cap height | Layout visual composition and font-metric tests | accepted |
| R350-09 label/mark paint | `test_label_and_mark_visuals_use_distinct_completed_paint_roles` | accepted |
| R350-10 bounded raster | Controller Z `programme-mark.png`, catalog/closure tests; `test_public_icon_evidence_is_bounded_and_decodes_its_purpose_built_raster` | accepted |
| R350-11 draft authoring | CLI `--icon-catalog`, README, Specification 64, draft closure tests | accepted |
| R350-12 release accountability | this matrix and R7 release review | R7 pending |

## R6 remaining evidence

The current public Controller Z icon slide demonstrates direct/trailing and
encoded selection plus a vector title visual and raster mark. R6 must still add
public imported Lucide/Tabler corpus fixtures. These are not implied by the
implementation tests above.
