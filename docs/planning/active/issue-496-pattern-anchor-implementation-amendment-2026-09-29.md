# #496 Slice 2 pattern anchor amendment

**Design/review:** [correction](../../design/issue-496-pattern-anchor-correction-2026-09-29.md), [architecture review](../../reviews/current/issue-496-pattern-anchor-architecture-review-2026-09-29.md). Amend the [implementation plan](issue-496-theme-asset-catalogues-implementation-plan-2026-09-28.md) only for Slice 2.

`layout/pattern_placement.py` receives the completed Rect geometry and returns region=clip=Rect bounds, origin=Rect top-left, and the completed corner shape. Scene v0.7 records these values; SVG serialization uses them without choosing a phase or clip. Add focused tests for translated Rects, rounded Rect clipping, and SVG/PNG phase parity. Existing v0.6 bytes remain unchanged; no Slice 3/4 scope change.

In Slice 2, `layout/mark_geometry.py` and `layout/lane_mark_facets.py` preserve
catalogue `Q` commands and source stroke width/cap/join, scale width with the
mark fit, and use it in lane footprints. Typed Layout-to-Scene parts and Scene
paint carry the completed stroke values; tests compare glyph SVG and resvg PNG
and ensure inline #464 glyph output remains unchanged.
