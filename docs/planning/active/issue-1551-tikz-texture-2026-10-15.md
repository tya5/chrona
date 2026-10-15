# Issue 1551: TikZ lowers the canvas texture as one pattern, not thousands of tiles

Status: design note, 2026-10-15. Base: `origin/main` 6a7d094e6. Refs #1551.
Source: the issue body and the reviewer comment (prefer one clipped pattern fill; refuse, counted,
only if the measured appearance cannot match; verify by compiling the whole titlecard `.tex` in Tectonic).

## Finding

Scene is already compact: the titlecard canvas texture is ONE `Rect` primitive (`canvas-texture`, 1600 x 874) with
one `PatternGeometry` (catalogue `hexagon-lattice`, tile 12.12 x 21, angle 0, origin (0, 0)). The SVG renderer writes
one `<pattern>` and one `fill="url(#...)"`. The blow-up is only the TikZ lowering (`_pattern_rect` in
`renderers/v05_typeset.py`): it enumerates `repeat_cells` (about 2060 cells), each a scope with its own clip and the
whole tile, 7.5 MB of TeX. No Scene change, so no contract change.

## Rule

For a catalogue pattern (tile primitives present) at angle 0 and full opacity, TikZ declares one
`\pgfdeclarepatterninherentlycolored` per distinct tile and fills the Rect with `pattern=<name>`; rounded corners stay on
the fill path. The tile body is written in pgf's basic layer: a tikzpicture or any box inside the body leaks into the page
when pgf runs it (measured: an overfull line shifted the whole slide 29 pt). A pgf pattern is anchored at the page's
lower-left corner with y up (measured) and cannot be rotated, so the body is drawn flipped and offset by the Scene origin's
phase, as up to four translated copies of the tile (the pattern bounding box clips each; each copy also clips to its own
tile, as the expansion does). Rotated or translucent patterns (the 45 degree bezel, tab and legend swatches: a few tiles
each) and the legacy line patterns keep the existing per-tile expansion, which is exact and small. Typst is unchanged (it
compiled). Raster checks need care: pdfium rounds a pattern cell up to whole pixels, so equality with the expansion is
measured at 32 px/pt, not at the 4 px/pt the other compile tests use.

## Acceptance rows

| # | Row | Basis | Evidence |
| --- | --- | --- | --- |
| 1 | The whole titlecard `.tex` compiles in Tectonic | issue body; reviewer comment | opt-in compile test; local compile; typesetter-compile run |
| 2 | One pattern declaration, not thousands of tiles; output bounded and deterministic | reviewer comment | unit tests on size, declaration count, repeat render |
| 3 | Appearance matches the SVG render, difference reported | reviewer comment ("measured appearance") | PNGs of both read by eye, pixel diff against the expansion |
| 4 | Counted refusal only if appearance cannot match | reviewer comment | not needed unless row 3 fails |
| 5 | Gap report row `tikz-horizontal-scale-refused` updated | issue follow-up | `docs/diagnostics/titlecard-vocabulary-gaps.md` |

Files: `src/chrona/presentation/renderers/v05_typeset.py`, one unit test file, one opt-in compile test, the gap report.
No `examples/**` edit and no generated file.
