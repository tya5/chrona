# Issue #46 implementation status

## Published implementation

- View typed facets, formatters, row index, target labels, axis, markers, shading, and numbered annotations.
- Scene rendering for configured axes, as-of markers, plot labels, numbered anchors, and summary figures.
- Typed summary schema/resolution and HALCYON-1 Project/View/Layout/Theme/Color Scheme/Actual/Summary/Context resources.
- Per-slide materializer context selection.

## Verification status

Focused tests were added but not executed here. Per user instruction, full `pytest` is delegated to a separate AI. Public materialization of `mission-brief`, `programme-board`, and `launch-campaign` must be run against this latest checkout using `tools/materialize_example.py`; generated SVGs must be written only by that public tool.

## Gate

Issue #46 remains open until those commands succeed and their SVG evidence is published. No manually authored SVG is accepted.