# Design: Target Parts as a Packaged Theme Asset Catalogue (#718)

**Status:** Proposed. Depth C: resources, YAML, tests and documentation only.
**Base:** `main` at `4981db0a`. Design plan:
[issue-718-target-parts-catalogue-design-plan-2026-10-02.md](../planning/active/issue-718-target-parts-catalogue-design-plan-2026-10-02.md).
Architecture review (accepted with three conditions, C1 to C3):
[issue-718-target-parts-catalogue-architecture-review-2026-10-02.md](../reviews/current/issue-718-target-parts-catalogue-architecture-review-2026-10-02.md).
**Normative contracts used, not changed:** [Spec 64](../specification/64-portable-icon-catalogs.md) section 8
(Theme glyph and pattern assets), [Spec 07](../specification/07-style-and-theme.md) section 5.2 (symbol and pattern
tokens), `schemas/theme-asset-source-v0.1.schema.yaml`, `schemas/icon-catalog-v0.4.schema.yaml`.

## 1. Decisions

### D1. One new set, not an edit of the starter

Add the resource set `chrona-target-parts` (alias `target-parts`), id `chrona-target-parts-v2026-10`, beside
`chrona-theme-starter-v2026-09-29`. The starter is pinned by SHA-256 in `presets/library.yaml`; editing it changes a
pinned closure for `technical-print`. The starter's glyphs are single-part simplifications, while this catalogue
extracts the targets' own drawings, multi-part and with outline twins. Entry names are namespaced by set, so
`chrona-starter:pin` and `chrona-target-parts:pin` coexist.
*Reverse:* delete the four resource files and their test and list entries; nothing else references them.

### D2. Glyphs and patterns only; frames and stamps are glyphs

The only ingress, `theme-asset-source/v0.1`, produces `glyphs` and `patterns` and writes `icons: {}`. The v0.4
schema also retains vector `icons`, but the importer cannot produce them; adding that branch is an importer change
and out of depth C. A raster container image (#465) cannot be bundled (bundled catalogues are vector-only, #715
decision B). So every part of the issue's table is a glyph or a pattern:

| Kind | Family | Consumer today |
| --- | --- | --- |
| gate glyphs | glyph | `milestoneSymbol`, `milestoneSymbolActual`, `milestoneSymbolBaseline` (Theme v0.13) |
| patterns | pattern | the Rect-only role/property pairs of Spec 07 |
| frames, borders, corners | glyph | **none**: no role paints a frame glyph |
| seal stamps | glyph | **none**: annotation kinds cannot select a stamp |

**What is missing, and where it is recorded.** Stamps and frames need a Theme role that places a catalogue glyph
on a surface other than a milestone: a per-kind annotation stamp (#584), a repeated-glyph title border and panel
corners (#587). Defining that role is a Theme schema change, so it stays in those issues. This design does not add
a role, a schema field or an importer branch. The entries are still useful now as the extracted, licensed geometry
and, technically, as milestone glyphs (the product accepts every glyph as a gate symbol; checked).
*Reverse:* if #584 or #587 chooses vector `icons` for these, the same geometry is re-issued under that family by
a later source version; the glyph entries are then removed in a new catalogue version, never edited in place.

### D3. Outline twins are explicit entries

A baseline gate draws as the glyph's outline. Spec 07 already turns every part of the glyph into a stroke when the
baseline role resolves to the outline treatment, so a Theme can reuse the solid glyph. Two cases need an explicit
stroke-only entry: a Theme that binds `milestoneSymbolBaseline` to its own asset (a ghost sprite), and Yuya's
baseline lantern, which has cap lines and a body outline but no ribs. So each gate glyph has a `-outline` twin made
of stroke parts only. The dash is a Theme property and is not in the asset.

### D4. The seals are original monoline strokes

`危` and `記` are drawn as stroked paths: a rounded-square frame plus the character as 6 and 8 monoline strokes
fitted to the seal. They are original geometry, drawn by looking at the glyph shape; no font outline is copied,
and there is no `text` element (forbidden). The bundled Noto fonts are OFL-licensed and were used only as a
visual reference while drawing. Rejected: tracing or converting font outlines (a derivative of a font file with its
own notice and reserved-name terms, not "original work, MIT" as the issue requires), and text in the glyph.
*Reverse:* replace the two entries in a new catalogue version.

### D5. Seigaiha stays with the starter; halftone is re-extracted as Ben-Day

`chrona-starter:seigaiha` already names Yuya's pattern (concentric semicircle scales on an 8 by 8 tile). A faithful
seigaiha has overlapping scales in which the front scale hides the arcs behind it. The closed pattern grammar has no
per-primitive substrate fill, no occlusion and no clip, and an arc needs its centre and every lowered point inside
the tile, so the exact picture needs a new primitive: a schema change. Stop and say so: seigaiha is **dropped from
this catalogue**, with the starter's entry as the shipped answer. Sunday's dots differ from the starter's `halftone`
in pitch and angle (6 units at 20 degrees against 8 units at 0), so they are extracted as `ben-day-dots`.

### D6. No builtin preset binds the new parts

`presets/library.yaml` and every bundle stay unchanged. Wiring a preset changes a builtin preset's rendered output
and belongs to preset assembly (#429 successor work). The catalogue ships as a wheel resource; a Theme author uses
it with `--icon-catalog PATH`, or copies it into a preset. *Reverse:* none needed.

### D7. The gallery generator lives with the research documents

`docs/research/presentation/target-parts-catalogue-2026-10/render_gallery.py` reads the shipped catalogue and draws it
with two Theme token sets. This follows `halcyon-1-target-design-2026-09-21/render_mocks.py`. Nothing under `src/`
(except the resources) or `tools/` is added or changed for the gallery.

### D8. Evidence for a resource-only change

A unit test pins the manifest, hashes, inventory and densities and regenerates the catalogue byte for byte from the
source, as the starter's test does. An integration test renders a Theme that binds a catalogue glyph and a catalogue
pattern through `chrona render` and checks the completed symbol and pattern in the Scene. The unit test also reads the four files through
the package resource API, and the implementation evidence lists the built wheel; no existing test or tool list is edited.

## 2. The catalogue

### Resource files (`src/chrona/resources/icons/`)

| File | Content |
| --- | --- |
| `chrona-target-parts-v2026-10.source.yaml` | the authored `theme-asset-source/v0.1` document, with the complete MIT notice |
| `chrona-target-parts-v2026-10.yaml` | the importer's canonical `icon-catalog/v0.4` output |
| `chrona-target-parts-v2026-10.manifest` | set, alias, SHA-256 of both files and of the notice, licence, entries, densities |
| `chrona-target-parts.NOTICE` | the MIT notice, byte-equal to `provenance.license.notice` |

The canonical catalogue is the importer's output; it is never edited by hand. Regenerating from the source must give
the same bytes (test). Names are lowercase kebab case, unique across glyphs and patterns (the importer rejects a
duplicate), with two suffix conventions: `-outline` is the stroke-only twin, and `-fine` / `-wide` are pitch variants.

### Glyphs (17)

| Entry | Viewport | Parts | Drawn from |
| --- | --- | --- | --- |
| `lantern` | 24 x 24 | 6 | Yuya: two caps and a body in four bands; the gaps stand for the rib lines, which a one-colour glyph cannot overlay |
| `lantern-outline` | 24 x 24 | 3 | Yuya baseline lantern: two cap lines and a body outline |
| `hexagon`, `hexagon-outline` | 24 x 24 | 1, 1 | Title Card: regular flat-top hexagon |
| `pin`, `pin-outline` | 24 x 24 | 1, 1 | Tenth Frame: the pin silhouette; the two stripes are holes in the fill |
| `star`, `star-outline` | 24 x 24 | 1, 1 | Sunday: five points, inner ratio 0.45 |
| `diamond`, `diamond-outline` | 24 x 24 | 1, 1 | Marquee and target B |
| `scroll-frame` | 48 x 64 | 6 | Yuya hanging scroll: hanger cord, two rods with knobs, mounting ring |
| `clipping-edge` | 64 x 8 | 1 | Marquee clipping: a deckled, torn-paper edge ribbon |
| `bulb` | 16 x 16 | 2 | Marquee: lit core and glass ring (glow is a Theme treatment, #587) |
| `panel-corner` | 16 x 16 | 2 | Sunday: heavy L bracket and a fine inner rule |
| `hazard-tab` | 56 x 24 | 8 | Title Card kind corner: outlined tab with 45 degree stripes |
| `seal-risk`, `seal-note` | 32 x 32 | 7, 9 | Yuya seals `危` and `記` |

Rules every glyph follows: parts are `fill` or `stroke`, never both; a stroke part carries its width, cap and join;
a hole is a sub-path wound opposite to its host, so the default non-zero fill leaves it empty (the adapter writes no
fill rule); circles and curves are quadratic chains of at most 22.5 degrees (15 degrees for the lantern bands);
no coordinate is negative or beyond the viewport, and strokes keep at least half their width of margin. Mark fit
scales stroke width with the path.

### Patterns (9)

| Entry | Tile | Angle | Primitives | Drawn from |
| --- | --- | --- | --- | --- |
| `hatch-fine`, `hatch`, `hatch-wide` | 4, 5, 6 | 45 | one centred line (1.3, 2, 2 wide) | the 45 degree hatch in ten of the 14 targets and in target B |
| `hazard-stripes` | 12 x 12 | 45 | one 6 wide rectangle | Title Card |
| `ben-day-dots`, `ben-day-dots-fine` | 6, 5 | 20 | one circle (r 1.35, 1.1) | Sunday |
| `bulb-row` | 14 x 14 | 0 | one circle (r 3) | Marquee bulb pitch |
| `hexagon-lattice`, `hexagon-lattice-wide` | 12.124 x 21, 27.713 x 48 | 0 | eight lines forming a periodic honeycomb (r 7 and 16) | Title Card |

A stripe is centred in its tile because the adapter clips a pattern to its tile: a stripe on the tile edge would
paint half its width. Lines that lie on a tile edge in the lattice are included on both edges for the same reason.
Densities are computed by the importer and pinned in the manifest.

### What is deliberately not in the assets

Colour (every part paints from the Theme role), the glow of a bulb or lantern, dash patterns, the baseline's
outline treatment, wobble, tilt, light cones, gradients, text and any image. Those are Theme treatments or open
knob issues.

## 3. Rules from Spec 64, checked

| Rule | How it holds |
| --- | --- |
| monochrome shapes only | the importer admits only path parts and circle, rect, line, arc pattern primitives |
| either filled or stroked | the `paint` field is one of the two; fill parts forbid stroke fields |
| no literal colour, gradient, filter, mask, clip, `style`, class, `transform`, `use`, `defs`, text, image | the source grammar has none of them; the whole source is rejected on any unknown key |
| multi-part glyphs paint parts from Theme roles | parts carry no colour; Spec 07 gives every part the role colour or the outline stroke |
| provenance and licence | original work, MIT, complete notice in the catalogue and as a `.NOTICE` file, SHA-256 of the source in the catalogue and of every file in the manifest |
| failure behaviour | the importer writes nothing if any entry is rejected; an unknown `set:name` fails with `E_THEME_ASSET_REFERENCE` at the Theme pointer (existing) |

## 4. Licence and provenance

Every part is original geometry written for this repository from the structure of the hand-drawn target pages, which
are themselves the owner's approved design targets in this repository. No third-party asset, icon set, font outline
or image is imported. The catalogue and notice are MIT, copyright "Chrona Contributors", as for the starter.

## 5. Target READMEs

Each of the 14 target READMEs, and the older target B README, gains a short section that lists which of its parts are
in the catalogue (or the starter), and which of #582 to #588 it still needs before its preset can be assembled. The
section lists only what the target's own table already says it lacks; it adds no new requirement.

## 6. Responsibility and extension points

The catalogue is data owned by the resource layer; the Theme chooses an entry by `set:name`; Layout fits it; Scene and
adapters carry completed geometry. A later version of the catalogue is a new id and set pin, never an in-place edit.
The extension points are the two open ones in D2 (a frame or stamp role) and D5 (an occluding pattern primitive).
