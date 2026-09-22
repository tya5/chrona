# Gantt Comparison Release Gate — I58-5 Implementation Plan

**Status:** Release-gate design and execution plan. Begins after I58-4 merge `ba05b07`.

## Scope

I58-5 changes no product policy. It verifies the merged I58-1 through I58-4
surface as one release candidate: structural placement ownership, all focused
acceptance coverage, full tests/conformance, byte reproduction, and declared
viewport raster review. A failing check returns work to the owning prior slice;
this gate never masks it with output editing.

## Execution unit

1. Record the main commit and inspect the acceptance matrix A58-01…A58-09.
2. Run focused structural/placement tests and the full test suite.
3. Run every public materializer check without writing outputs.
4. Rasterize and visually inspect the three HALCYON outputs at declared viewport
   sizes; confirm headers, legends, labels, table text and dependencies are legible.
5. Publish a release review with commands, results, artifact scope, architecture
   consistency, and residual-warning disposition. Only then close #58.

## Architecture review criterion

The release evidence must show the same ownership at every entry point:
Project facts and View/Detail/Layout/Theme declarations enter Layout; Layout
returns placements and diagnostics; Scene only projects them; SVG/PNG only
serializes or provides evidence. No release-only branch or renderer fallback is
permitted.
