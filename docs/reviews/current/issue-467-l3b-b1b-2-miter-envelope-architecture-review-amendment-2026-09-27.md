# #467 B1b-2 Miter Envelope: Architecture Review Amendment

**Reviewed baseline:** public `074bd55590961376c557dac9356a2121e047909a`.
**Amends:** [B1b-2 architecture review](issue-467-l3b-b1b-2-stroke-aware-footprint-architecture-review-2026-09-27.md) and [miter-envelope design amendment](../../design/issue-467-l3b-b1b-2-miter-envelope-amendment-2026-09-27.md).

## Evidence and decision

The predecessor's miter-limit-four gate is not satisfied by all admitted adapters. `src/chrona/presentation/renderers/v05_typeset.py` emits TikZ general paths without an explicit miter limit; [TikZ path actions](https://tikz.dev/tikz-actions) documents default miter limit 10. `src/chrona/presentation/renderers/v05_svg.py` leaves the SVG property unspecified; the [W3C default](https://www.w3.org/TR/fill-stroke-3/#StrokeMiterlimitProperty) is 4, and PNG is derived from SVG. Typst rejects general paths, so it does not admit this geometry. PDF is routed through `svg2rlg` and ReportLab in `src/chrona/presentation/renderers/registry.py`, with exact versions pinned in `pyproject.toml` (`svglib==2.2.0`, `reportlab==5.0.1`); the supported PDF stroke-join limit is 10 per the [Adobe PDF Reference](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf). These adapter facts invalidate the old ≤4 gate.

The approved correction is a target-independent 10× stroke-width expansion per side for stroked path control-point envelopes. This conservative geometry avoids adapter-specific Layout policy, retains ScenePaintResolver as the single paint conversion boundary, and leaves ScenePaint/adapter output unchanged. It is consistent with geometry-only Layout ownership and collision-clearance separation in Specs 38/46 and does not change semantics in Theme, View, or Project. Rectangles and segments keep their existing distinct single-stroke accounting. No issue acceptance criterion is thereby met.

## Architecture check and remaining gate

Whole-architecture review finds the bound localized to Layout's visible geometry footprint; Scene still projects completed geometry and paint, adapters serialize, and no renderer repairs geometry. The larger bound may increase conservative false collisions. The 02 ≤12 criterion remains a hard feasibility gate after implementation; a failure requires return to design, not relaxation, target-specific allocation, or adapter miter changes. Preserve the predecessor's independent geometry ownership migration and byte-characterization requirements. Implementation planning may proceed against the corrected Specs; lane activation remains gated by measured feasibility and every literal acceptance row.
