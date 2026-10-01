# Design Plan: Target Parts as a Packaged Theme Asset Catalogue (#718)

**Status:** Proposed. Depth C (resources, YAML and docs only; no core, schema or importer change).
**Base:** `main` at `4981db0a` (observed 2026-10-02). Issue #718 is open; it has no comments before the claim.
Product code is not changed by this document.

## Objective

Extract the reusable design parts of the 14 hand-drawn targets (PR #461,
`docs/research/presentation/*-target-2026-09-26/`) as monochrome Theme assets in one packaged
catalogue, so that the target presets can later be assembled in YAML. A part is geometry only:
colour, glow, dash and every other treatment stay with the Theme (Spec 64 section 8).

## Verified starting point

Published on `main` and checked by running the importer and the render path in a scratch workspace.

- **A packaged Theme asset catalogue already exists.** `chrona-theme-starter-v2026-09-29`
  (#496, MIT, set `chrona-starter`) ships seven glyphs (`chest`, `diamond`, `hexagon`, `lantern`,
  `pin`, `star`, `ticked-circle`) and six patterns (`halftone`, `seigaiha`, three ordered dithers,
  `dense-hatch`). Its bytes are pinned by SHA-256 in `presets/library.yaml` for the `technical-print`
  preset, so editing it would change a pinned identity. Its glyphs are single-part simplifications,
  not the targets' drawings.
- **The only ingress for new Theme assets is `theme-asset-source/v0.1`.** The importer
  (`chrona.presentation.icons.importer.import_theme_assets`) admits exactly `glyphs` and `patterns`
  and writes `icons: {}`. Glyph parts are `paint: fill|stroke` over the path subset `M L H V Q Z`
  (relative forms allowed; `C` and `A` are rejected), with coordinates inside the viewport. A pattern
  is a tile of at most 64 circles, rectangles, lines and arcs, all inside the tile, with an exact
  recomputed density. There is no colour, clip, per-primitive substrate, text or image.
- **Consumers.** A catalogue glyph is bindable only on `milestoneSymbol`, `milestoneSymbolActual` and
  `milestoneSymbolBaseline`; a catalogue pattern only on the ten Rect-only role/property pairs of
  Spec 07 (for example `axis-band-decoration2.pattern`, `progress-fill.pattern`, `missing-actual.pattern`).
  A role whose paint resolves to the outline treatment draws every glyph part as a stroke (Spec 07).
  Every part paints from the one role colour; a glyph part cannot declare a colour.
- **A render check.** A scratch Theme binding a catalogue glyph and a catalogue pattern renders through
  `chrona render --theme ... --icon-catalog ...` to SVG and PNG, so the path from catalogue to pixels is
  open for gates and patterns. For frames and stamps it is not (see "Open decisions", D2).
- **Open knob issues.** #582 named date ranges, #583 group header identity, #584 annotation kinds
  (stamps), #585 text treatments, #586 derived header figures, #587 surface decoration (canvas texture,
  repeated-glyph title border, panels), #588 hand wobble and affixes. #464 (gate glyphs), #465 (container
  PNG) and #496 (asset catalogues) are closed.

Inferred, not verified: that a future role will accept a frame or stamp glyph (no such role is specified
today), and how a Theme author will want parts grouped. Unverified: the visual quality of a part at the
size a gate takes in a real board; the gallery and the scratch renders are the evidence for that.

## Literal acceptance (copied from the issue)

1. A packaged theme-asset-source catalogue (for example `chrona-target-parts-v2026-10`) contains every
   part in the table, or lists why a part was dropped. It passes the Spec 64 importer with no rejected
   element.
2. A catalogue gallery page (committed SVG and PNG) shows each part at two sizes and in two Themes,
   proving that color comes from the Theme.
3. Each target README records which of its parts are now in the catalogue, and which knob issue
   (#582 to #588) the target still needs before its preset can be assembled.
4. No file under `src/` other than packaged resources changes. No schema changes.

The issue's rules are also acceptance conditions: monochrome shapes only, each shape either filled or
stroked, no literal colours, gradients, filters, masks, clips, `style`, class, `transform`, `use`, `defs`,
text or images; multi-part glyphs paint their parts from Theme roles; effects such as glow, gradients and
the as-of cone are not part of this issue; each asset carries provenance and licence (original work,
MIT, with a content hash).

## Parts inventory (the issue's table, with what each target draws)

| Kind | Part | Target source | Planned entry |
| --- | --- | --- | --- |
| gate glyph | lantern with caps and ribbed body; its baseline form: cap lines and a body outline | Yuya `lanternGlyph` | `lantern`, `lantern-outline` |
| gate glyph | hexagon | Title Card `hex` | `hexagon`, `hexagon-outline` |
| gate glyph | bowling pin with two stripes | Tenth Frame `pin` | `pin`, `pin-outline` |
| gate glyph | star | Sunday `star` | `star`, `star-outline` |
| gate glyph | diamond | Marquee, target B | `diamond`, `diamond-outline` |
| pattern | halftone dots (Ben-Day, 20 degrees) | Sunday `dots` | `ben-day-dots`, `ben-day-dots-fine` |
| pattern | seigaiha | Yuya `wave` | not extracted: see D5 |
| pattern | hexagon lattice | Title Card `hexwin`, `hexbg` | `hexagon-lattice`, `hexagon-lattice-wide` |
| pattern | hazard stripes | Title Card `hazard` | `hazard-stripes` |
| pattern | hatch (45 degrees; 4, 5 and 6 unit pitch) | target B, Yuya, Marquee, Swiss and others | `hatch-fine`, `hatch`, `hatch-wide` |
| frame | hanging-scroll mounting | Yuya `掛軸` | `scroll-frame` |
| frame | newspaper-clipping edge | Marquee extras | `clipping-edge` |
| frame | bulb border element | Marquee `bulb` | `bulb`, `bulb-row` |
| frame | inked panel corner | Sunday `panel` | `panel-corner` |
| mark | seal stamp, drawn as strokes not text | Yuya `危` `記` | `seal-risk`, `seal-note` |
| mark | kind corner | Title Card hazard tab | `hazard-tab` |

Out of the table and left alone: the built-in circle and diamond marks, the starter's `chest` and
`ticked-circle` (RPG, Flatpack), and the other targets' texture patterns (checker, scanline, grid, dither).

## Dependencies

#464, #465 and #496 are closed and provide the glyph, container and catalogue mechanisms. The knob issues
#582 to #588 are open and are not prerequisites: this issue provides the parts, and each README names the
knob a target still needs. #715 decision B keeps `icon-catalog-v0.3` for the Material catalogue; this
catalogue is `v0.4` and vector-only.

## Open decisions (closed in the design)

- **D1.** A new set or an extension of the starter.
- **D2.** The catalogue family for frames and stamps, given that the importer admits only glyphs and patterns.
- **D3.** Explicit outline entries or the Theme's outline treatment alone.
- **D4.** How to draw `危` and `記` without text, without an unclear licence.
- **D5.** Whether to re-extract seigaiha and halftone, which the starter already names.
- **D6.** Whether any builtin preset binds the new parts in this issue.
- **D7.** Where the gallery generator lives, given the depth-C boundary.
- **D8.** The test and packaging evidence for a resource-only change.

## Responsibility boundaries

The catalogue owns normalized geometry, identity and provenance. The Theme owns role paint, variant choice and
treatments (outline, dash, opacity). Layout owns mark fitting and pattern placement. Scene and adapters carry
completed geometry. This issue touches only the first: a resource, its manifest and notice, tests that pin it,
and documentation. It adds no role, schema, importer branch or preset binding.

## Data and resource model

One catalogue resource triple, in the starter's shape: `<id>.source.yaml` (the authored `theme-asset-source/v0.1`
document, with the complete notice), `<id>.yaml` (the importer's canonical output, `icon-catalog/v0.4`) and
`<id>.manifest` (set, aliases, SHA-256 of both, licence, entry inventory, densities), plus one `.NOTICE` file.
Entries are identified as `chrona-target-parts:<name>`.

## Migration effects

None. No existing resource, schema, pin or example changes. The new files are additive packaged data.

## Design review questions

- Does any decision need a new resource kind, schema, role or importer change? If so it stops at the design.
- Do stamps and frames, which no role can paint today, still belong in a glyph catalogue, and is the gap recorded
  against the right knob issue?
- Is every part original work or drawn from a source with a clear licence, and does each carry the notice?
- Are the new entries distinguishable from the starter's, and is the wheel budget respected?

## Acceptance evidence

The committed catalogue, source, manifest and notice; the importer reproducing the catalogue bytes exactly; a
scratch render through the real product for every glyph and every pattern; the gallery SVG and PNG, inspected;
the 14 target READMEs; the wheel size before and after; green three-OS CI on the commit that publishes the
acceptance review.

## Order of slices

1. Design plan (this document). 2. Design. 3. Architecture review. 4. Implementation plan.
5. Catalogue, tests and packaging. 6. Gallery and target READMEs. 7. Acceptance review and release check.
Each is a separate small pull request that references #718 without a closing keyword.
