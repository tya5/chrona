# #496 pattern anchor correction

**Status:** Accepted before Slice 2 implementation. **Base:** #496 selected design and Specification 08 §4.0.1.

The selected design assigned region, clip, and tile origin to Layout but did not fix their coordinates. For every patterned Rect, Layout uses the completed Rect bounds as the repeated region and clip, and its top-left as the tile origin. Rounded Rects retain their completed corner clip. This makes the repeat phase deterministic for each mark or decoration; Scene only carries these values and adapters only serialize them. No Theme, catalogue, density, or existing Scene v0.6 behavior changes. A different cross-mark phase alignment would require a separate design decision.

Catalogue glyph stroke parts expose another previously unspecified handoff:
Layout scales each source-unit `strokeWidth` by the same uniform fit factor as
the normalized path and retains its `lineCap`/`lineJoin`. Theme supplies stroke
color, not a replacement width; a catalogue stroke part does not require a
redundant Theme `strokeWidth`. The typed Layout part and lane footprint carry
the completed width/finish into Scene paint. Inline #464 glyph semantics and
public Scene v0.6 output do not change. Quadratic `Q` paths use the existing
Layout path-command representation.
