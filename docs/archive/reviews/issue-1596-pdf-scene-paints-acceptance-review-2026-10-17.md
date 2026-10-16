<!-- chrona:literal-acceptance/v1 -->

# Completed PDF marker and pattern paints

Public base `7b14d47bb`; implementation `95c853e2d`, reconciled at `878b08805`.
[Design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1596#issuecomment-6219479094).
Final-head [CI38933784788](https://github.com/tya5/chrona/actions/runs/38933784788)
and exact review-containing main `9edbfface85256e7c5541dd6fef0beb60379d536`
[three-OS release38935507051](https://github.com/tya5/chrona/actions/runs/38935507051)
passed; the issue is closed.

## Literal issue acceptance

### Issue #1596

- Source: [Issue #1596](https://github.com/tya5/chrona/issues/1596)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a relation with an end marker and a hatched paint appear in the PDF content (operators present). | met | [PDF paint controls](../../../tests/unit/chrona/presentation/renderers/test_pdf_scene_paints.py): actual PDF fill/stroke/clip/transform operators, both marker sides, physical/stroke-relative units, quadratic tangents, completed wobble, legacy/catalogue repeats, phase/rotation/containment and counted unsupported-host refusal. Combined PDF/font/registry/viewer-fit and empty-source allocation batch after reconciliation:96 passed in43.67s. | — |
| 2 | The command above, viewed: arrowheads and hatch present, matching the PNG. | met | Exact [#1582 CSV](https://github.com/tya5/chrona/issues/1582), `chrona render --preset target-b --actual actual.yaml --output x.pdf project.yaml`, no extra View/profile. Root viewed PDFium raster beside the equivalent PNG after latest-main reconciliation: route and legend arrows and hatched legend swatch present, with the empty rail reclaimed. Final local evidence: `/private/tmp/chrona-1596-final-render.Ttr3az/target-b.pdf`, `target-b-pdf.png`, `target-b.png`. PDF contains22 clipping and67 fill operators. | — |
| 3 | Public SVG/Scene byte-identical. | met | Final source7d756d84f [artifact12060575854](https://github.com/tya5/chrona/actions/runs/38933784788/artifacts/12060575854) against ready7b14d47bb:109 paths,0 added/retired, all50SVG+50Scene byte-identical. Only the generated diagnostics inventory changes (three existing diagnostic codes gain PDF lowering sites, registry source locations shift); the other108 files are identical. [Final audit](https://github.com/tya5/chrona/pull/1604#issuecomment-6220280579). | — |

## Programme-level criteria (optional)

Adapter-private vector lowering reuses completed marker transforms and repeat
cells; no Layout, Scene, schema, routing or font-selection policy changes.
Spec08 is aligned with Spec63's painted wobble outline; independent review's
nominal-tangent finding is corrected and tested. Default SVG namespace is
preserved so svglib retains existing and new clips. Closed-face font embedding
and raw text/viewer-fit controls pass. No examples or generated outputs edited.
Spec63 target-profile refusals remain unchanged; this adds no rich PDF profile.
