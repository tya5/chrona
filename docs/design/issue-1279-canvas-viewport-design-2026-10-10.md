# Issue #1279 — declared canvas extent diagnostic

[Plan](../planning/active/issue-1279-canvas-viewport-design-plan-2026-10-10.md).
Normative authority: Specification 33 §13; report transport: Specs 08 §8 and 66 §3.

## Contract

Capture an immutable `DeclaredViewport` before content-size allocation: positive
inline size, and positive block size or `None` for Draft auto block. Its origin
is zero. The adjusted LayoutManifest remains the allocation, never the declaration.
The use case supplies this fact to both Layout request paths; no declaration means
no comparison, not an invented limit from the allocation.

Layout compares the completed canvas's start and end on every declared axis,
using its existing coordinate tolerance. A negative inline origin is overflow
even if width alone fits. Auto block does not constrain either block edge.
Produce exactly one typed `CanvasViewportWarning` for an overflowing surface;
fitting surfaces produce none. Preserve the canvas and all primitive geometry.

The record carries surface identity, `/body/environment/viewport`, `declared`
inline/block sizes (block may be null), `actual` inline/block starts and sizes,
and up to five largest `contributors`. Attribute completed geometry to its native
slot, union bounds per slot, and record positive start/end overruns on declared
axes. Sort by descending maximum overrun then slot identity; report the total
contributor count. Include allocated slots and frame extents, but exclude canvas
textures/overlays generated from the completed canvas itself. Contributors are
explanatory evidence; they neither choose nor recompute geometry.

## Boundaries and migration

Layout owns comparison and attribution for table-timeline and dependency-network.
Scene projects the immutable warning as runtime metadata; it must not compare
bounds. The shared warning ledger emits `W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT`, stable
identity `(surfaceId, sourceRef)`, structured facts and a readable cause/subject.
Inspection Scene diagnostics and CLI/MCP reports retain the same identity.
Adapters, Core, View, Theme and resource schemas gain no policy or syntax.

This intentionally adds reports on existing overflowing renders, not clipping,
resizing, layout fallback, or a strict refusal. Unconstrained auto height stays
unwarned; independently overflowing inline extent still warns. Router, axis-label
and tall-output fixes remain #1292/#1291/#1299. No corpus exceptions or edits.
