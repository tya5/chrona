# #496 pattern anchor architecture review

**Decision:** Accept the [correction](../../design/issue-496-pattern-anchor-correction-2026-09-29.md) and Specification 08 §4.0.1 update before Slice 2 code.

The rule uses Layout's existing completed Rect bounds and corner geometry, leaves Theme/asset identity and intrinsic density in their declared owners (Specifications 07/64), and gives Scene v0.7 a fully specified geometry handoff. SVG/resvg share that completed phase and clip; adapters do not infer anchors. Scene v0.6 and existing flat treatments remain unchanged. Review risk: repeated patterns on adjacent Rects restart at each Rect; this is intentional, not a page-global lattice.

The same review closes the catalogue glyph stroke handoff in Specification 64:
source width/finish remain geometric, Layout scales and includes them in lane
footprints, and Scene/adapter only paint the completed stroke with Theme color.
This preserves #464 inline glyphs, prevents Theme width from silently
distorting a normalized asset, and adds no new resource version.
