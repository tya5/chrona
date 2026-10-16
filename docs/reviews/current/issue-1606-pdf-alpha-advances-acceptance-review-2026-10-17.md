<!-- chrona:literal-acceptance/v1 -->

# Issue #1606 — PDF opacity and measured runs

Product source `5067c478c5aa16d24142d3a9d31d9155da72cf44`, ready base
`6bb56c205`. [Design and implementation plan](https://github.com/tya5/chrona/issues/1606#issuecomment-6225850393).
PDF serialization only: isolated transparency forms apply alpha once; run
origins consume completed advances. Layout, Scene, SVG and PNG are unchanged.
Independent read-only review found no ownership breach in these paths.

## Literal issue acceptance

### Issue #1606

- Source: [Issue #1606](https://github.com/tya5/chrona/issues/1606)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic test: a Scene rect with fill opacity 0.1 serialises to a PDF with that alpha (ExtGState or equivalent), and a small-caps run has the same advances as the PNG. | met | [Alpha tests](../../../tests/unit/chrona/presentation/renderers/test_pdf_opacity.py) verify fill/stroke alpha, isolated overlapping paint, nested transforms/clips, painter order and embedded closed fonts. [Run tests](../../../tests/unit/chrona/presentation/renderers/test_pdf_text_run_advances.py) verify measured prefix advances, tracking, compression, multiline baselines, rotation, whitespace and exact private face attributes. | — |
| 2 | The command above, viewed as a rasterised PDF next to the PNG: the shading and headers match. | met | Root rendered the unchanged public [CSV fixture](https://github.com/tya5/chrona/issues/1582) using `chrona render project.yaml --actual actual.yaml --preset sunday --output sunday.pdf` and the PNG counterpart, rasterized PDF with pypdfium2 at 4/3 scale and viewed both images. Weekend columns are faint grey in both; group-header run spacing matches. Local evidence: `/private/tmp/chrona-1606-pdf-alpha-advances-20261017/sunday{,-pdf}.png`. Existing profile omissions (wobble) and three suppressed relations are not changed by this PDF fix. | — |
| 3 | Public SVG/Scene byte-identical. | met | Official [artifact12078039812](https://github.com/tya5/chrona/actions/runs/38976475995/artifacts/12078039812) before/after archives contain 109 paths each: all 50 SVG and 50 Scene bytes identical, no additions/retirements. Only diagnostics inventory changes (one alpha validator entry and shifted source references). | — |

## Programme-level criteria (optional)

Focused validation: 20 alpha/run/paint tests passed; 70 existing PDF-font,
closed-map, target-registry and viewer-fit tests passed. Full CI, official
artifact audit and exact review-containing main three-OS release remain open.
