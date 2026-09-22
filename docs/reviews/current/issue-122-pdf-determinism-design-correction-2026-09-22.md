# Issue 122 — PDF Determinism Design Correction

## Evidence

The approved CairoSVG-only PDF proposal was tested against the completed
Controller Z SVG.  SVG and CairoSVG PNG reproduced bytes, but two CairoSVG PDF
conversions in one process differed in compressed PDF-stream bytes.  Pinning
CairoSVG 2.9.1 and Cairo 1.18.4 did not make the PDF artifact immutable.
`pikepdf` deterministic/static IDs did not normalize those stream differences.

## Corrected decision

- PNG remains the CairoSVG adapter, bound by `cairosvg`, `cairo`, and DPI.
- PDF is a separate `svglib + ReportLab` adapter.  It parses the completed SVG,
  serializes it through ReportLab, and sets `reportlab.rl_config.invariant = 1`
  for the conversion scope.  The same Chrona SVG then produced byte-identical
  PDF 1.4 artifacts in repeated runs.
- A PDF Context declares `environment.rasterizer` with `engine: reportlab`,
  exact `svglib` and `reportlab` versions, and `invariant: true`.  PNG retains
  the existing CairoSVG descriptor.  A target/backend mismatch rejects before
  artifact creation.

This is not a renderer policy change: each adapter consumes the common SVG
serialization of completed primitives only.  It makes the deterministic claim
true rather than weakening it to a semantic-only comparison.

## Implementation impact

The v0.7 schema uses a discriminated rasterizer descriptor.  The target registry
selects CairoSVG only for PNG and ReportLab only for PDF.  Optional dependencies
are declared as a presentation-export extra; either unavailable backend has the
same stable unavailable diagnostic.  PNG/PDF byte repeatability remains an
acceptance test.
