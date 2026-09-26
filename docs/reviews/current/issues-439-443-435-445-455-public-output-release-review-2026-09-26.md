<!-- chrona:literal-acceptance/v1 -->

# Release Review — Published P0 Output and Footer Geometry (#439, #443, #435, #445, #455)

## Literal issue acceptance

### Issue #439

- Source: [Issue #439](https://github.com/tya5/chrona/issues/439)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every axis label in every committed slide is visible in the rasterized output. | met | [all-SVG order guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [perceptibility gate](../../../tools/check_scene_perceptibility.py) | — |
| 2 | An opaque primitive painted over a text placement is diagnosed at layout, with the text's placement id. | narrowed | [Scene-level gate](../../../src/chrona/presentation/scene/perceptibility.py); [host/occlusion tests](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py) | [#446](https://github.com/tya5/chrona/issues/446) |
| 3 | Axis decorations sit below axis text because they declare it, not because of emission order. | met | [Layout paint/host closure](../../../src/chrona/presentation/layout/surface_composer.py); [Scene test](../../../tests/unit/chrona/presentation/scene/test_v05_builder.py) | — |
| 4 | `DVT Qualification` is visible inside its bar on all six controller-z slides, and the note-index badges are uncovered. | met | [six-slide order guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [perceptibility gate](../../../tools/check_scene_perceptibility.py) | — |
| 5 | No text placement in a committed Scene is covered by a later-painted opaque primitive. | met | [perceptibility gate](../../../tools/check_scene_perceptibility.py); [all public Scenes](../../../examples/README.md) | — |

### Issue #443

- Source: [Issue #443](https://github.com/tya5/chrona/issues/443)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No two axis labels on any committed slide have intersecting bounds, across tiers as well as within one. | met | [micro-point corpus guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [replan focused test](../../../tests/integration/test_materialize_example.py) | — |
| 2 | `06-flight-readiness` renders its rotated month labels without touching the quarter labels, and both are visible once #439 is fixed. | met | [flight-readiness SVG](../../../examples/halcyon-1/generated/06-flight-readiness.svg); [public materializer test](../../../tests/integration/test_materialize_example.py) | — |
| 3 | A tier with a rotated orientation reserves a lane as tall as its tallest rotated label. | met | [Layout lane allocation](../../../src/chrona/presentation/layout/surface_composer.py); [axis test](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py) | — |

### Issue #435

- Source: [Issue #435](https://github.com/tya5/chrona/issues/435)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No committed slide contains the table text `True` or `False`. | met | [corpus guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [boolean format tests](../../../tests/unit/chrona/presentation/model/test_surface_content.py) | — |
| 2 | A View whose column selects a boolean source without a declared presentation is diagnosed. | met | [View contract test](../../../tests/unit/chrona/presentation/contracts/test_contract_resources.py); [HALCYON View](../../../examples/halcyon-1/views/01-mission-brief.yaml) | — |
| 3 | The `table-missing-observation` evidence row in the realization report points at slides whose cells a reader can interpret. | met | [realization report](../../gallery/semantic-realization-coverage.md); [HALCYON mission SVG](../../../examples/halcyon-1/generated/01-mission-brief.svg) | — |

### Issue #445

- Source: [Issue #445](https://github.com/tya5/chrona/issues/445)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No text placement in a committed Scene extends outside its slot unless the slot's overflow policy allows it and the Scene records it. | met | [public perceptibility gate](../../../tools/check_scene_perceptibility.py); [overflow tests](../../../tests/integration/test_render.py) | — |
| 2 | `controller-z-ja/executive`'s group details and milestone digest are both legible. | met | [Japanese SVG](../../../examples/controller-z-ja/generated/executive.svg); [measured-block integration test](../../../tests/integration/test_materialize_example.py) | — |

### Issue #455

- Source: [Issue #455](https://github.com/tya5/chrona/issues/455)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No committed Scene has positive-area overlap between independently emitted project-note text placements in the same notes slot. | met | [corpus guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [note advancement test](../../../tests/integration/test_render.py) | — |
| 2 | Every `ellipsize-with-source` text placement lies inside its slot after closed visual reservations. | met | [corpus guard](../../../tests/acceptance/output/test_public_geometry_regressions.py); [programme-board Scene](../../../examples/halcyon-1/generated/02-programme-board.scene.json) | — |
| 3 | The corpus perceptibility audit has no exemption for either relationship. | met | [single evaluator](../../../src/chrona/presentation/scene/perceptibility.py); [public gate](../../../tools/check_scene_perceptibility.py) | — |
| 4 | Focused Layout, public materializer, generated Scene/SVG, and CI evidence pass. | met | [focused render tests](../../../tests/integration/test_render.py); [materializer tests](../../../tests/integration/test_materialize_example.py); [CI matrix](https://github.com/tya5/chrona/actions/runs/36207835457) | — |

## Programme-level criteria (optional)

The published 21 Scenes have zero perceptibility errors (1,924 informational
observations), with no issue-specific allowlist. Direct micro-point audit
found zero intersections among 164 axis labels, zero positive-area overlaps
among independent project notes, and zero ellipsis-legend inline escapes.
All 164 public SVG axis labels occur after their axis bands; the six
Controller-Z `DVT Qualification` inside labels occur after their bars. No
table-cell text is a raw Python boolean. Raster inspection of the Japanese
Controller-Z review shows wrapped, separated group details and milestone
digest; the HALCYON flight-readiness raster shows the quarter and rotated
month labels simultaneously without overlap.

The #439 issue comment explicitly moved its proposed occlusion diagnostic
from Layout into #446's single Scene-level perceptibility gate. That
replacement is marked `narrowed` above rather than claiming Layout emits
the diagnostic. #446 is already accepted and closed. Likewise #443's strict
zero-intersection public-corpus rule does not remove #449's explicitly
declared `visible-overflow` behavior for other author inputs.

The [568cc2f2 CI matrix](https://github.com/tya5/chrona/actions/runs/36207835457)
passed Ubuntu, macOS, Windows, wheel smoke, and newest-Python public
materializer reproduction. These are release reviews of published work; no
new Scene, adapter, or Layout policy is introduced here.

## Architecture conclusion

Layout owns measured axis lanes, host-relative paint order, paragraph and
footer geometry, and finite overflow completion. View owns boolean display
and elected axis thinning. Scene carries completed placements and the
separate #446 perceptibility evaluator observes them without repair. SVG
and other adapters only project supplied order/paint. The existing
implementation and the public artifacts satisfy these boundaries.
