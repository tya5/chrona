<!-- chrona:literal-acceptance/v1 -->

# Completed PDF marker and pattern paints

Public base `69a5a5ede`; implementation `95c853e2d`.
[Design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1596#issuecomment-6219479094).
Final-head CI, BOT byte audit and exact review-containing main three-OS release
remain required before closure.

## Literal issue acceptance

### Issue #1596

- Source: [Issue #1596](https://github.com/tya5/chrona/issues/1596)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a relation with an end marker and a hatched paint appear in the PDF content (operators present). | met | [PDF paint controls](../../../tests/unit/chrona/presentation/renderers/test_pdf_scene_paints.py): actual PDF fill/stroke/clip/transform operators, both marker sides, physical/stroke-relative units, quadratic tangents, completed wobble, legacy/catalogue repeats, phase/rotation/containment and counted unsupported-host refusal. Related PDF/font/registry/viewer-fit batch:41 passed,48 deselected in7.80s. | — |
| 2 | The command above, viewed: arrowheads and hatch present, matching the PNG. | met | Exact [#1582 CSV](https://github.com/tya5/chrona/issues/1582), `chrona render --preset target-b --actual actual.yaml --output x.pdf project.yaml`, no extra View/profile. Root viewed PDFium raster beside the equivalent PNG: route and legend arrows and hatched legend swatch present. Final local evidence: `/private/tmp/chrona-1596-render.X9mKhI/target-b-vectors.pdf`, `target-b-pdf.png`, `target-b.png`. PDF contains22 clipping and67 fill operators. | — |
| 3 | Public SVG/Scene byte-identical. | met | Official [derived snapshot](../../../tools/derived_workflow.py) against69a5a5ede completed:109 paths,0 added/retired, all50SVG+50Scene byte-identical. Only the generated diagnostics inventory changes (three existing diagnostic codes gain PDF lowering sites, registry source locations shift); the other108 files are identical. Final CI artifact must confirm the same bound. | — |

## Programme-level criteria (optional)

Adapter-private vector lowering reuses completed marker transforms and repeat
cells; no Layout, Scene, schema, routing or font-selection policy changes.
Spec08 is aligned with Spec63's painted wobble outline; independent review's
nominal-tangent finding is corrected and tested. Default SVG namespace is
preserved so svglib retains existing and new clips. Closed-face font embedding
and raw text/viewer-fit controls pass. No examples or generated outputs edited.
