# Portable Icon Catalogs and Theme Assets

**Status:** icon-only v0.3 retained; asset-catalog v0.5 contract selected in #849
**Owns:** local Iconify ingestion, licensed normalized icon/glyph/pattern
catalog entries, catalog-set closure, visual selection, completed Scene
primitives and paint, accessibility, and SVG/PNG target capability.
**Does not own:** Project facts, arbitrary images/artwork (§7 records the one
narrow exception: a purpose-built PNG entry reused as Theme-bound container
artwork), raw SVG at render time, concrete colours, Layout coordinates,
package acquisition, network fetching, target fallback, or PDF rich-paint
fidelity.

## 1. Contract and authority

```text
local Iconify JSON -> normalized catalog -> pinned Context catalog set
  + View visual request + Theme/Colour Scheme + Font metrics
  -> Layout visual/text placement -> completed Scene Icon -> adapter
```

An icon is a visual companion to an existing textual or semantic source. It
cannot be the only carrier of required meaning. View owns occurrence, catalog
reference, side, and field-to-icon mapping; Theme owns size ratio, gap ratio,
and visual paint; Layout owns all sizing, path transforms, stroke scaling,
cap-height alignment, measurement, wrapping, overflow, and reading order;
Scene projects completed primitives and `ScenePaintResolver` supplies their
completed paint; an adapter serializes only completed data.

The former v0.1 local-file catalog is superseded. No compatibility alias,
one-catalog bridge, raw-SVG fallback, or silently downgraded source is retained.

## 2. Local collection ingestion and normalized catalog

`chrona icon-catalog import COLLECTION.json --license-spdx SPDX --notice-file
NOTICE --output CATALOG.yaml` reads explicit local inputs only. The published
`@iconify-json/*/icons.json` files contain no license metadata, so the importer
must not infer or omit it: the author supplies the collection's SPDX identifier
and complete local notice file. It performs no network access, registry lookup,
package installation, or rendering. It validates every icon and writes the
destination atomically only if the complete collection succeeds. Failure
identifies `prefix`, icon name, source element/attribute/command, and stable
diagnostic; a partial catalog is never emitted.

The destination conventionally uses a `.yaml` suffix, but the importer writes
canonical JSON: JSON is a YAML subset and therefore remains a valid catalog
document while allowing the shared safe decoder's JSON fast path.

The successor `chrona/icon-catalog/v0.3` stores canonical normalized entries,
not source SVG paths. It records:

- one canonical `prefix`, non-empty aliases, source collection version and
  SHA-256 identity;
- declared license identifier and notice text/provenance;
- lexically ordered canonical entry names, an identity-closed alias-to-canonical
  mapping, viewport, alternative, and normalized
  monochrome vector payload; and
- optional identity-closed purpose-built PNG entry bytes addressed relative to
  the catalog revision.

`set:name` is the only authored vector/raster reference form. A Context catalog
set resolves the set against its catalog prefix and aliases. Duplicate prefix or
alias across the pinned set, duplicate name/alias in one catalog, unknown set,
unknown name, or ambiguous reference rejects before Layout. Catalog order is
canonical lexical prefix order after validation, not Context input order.

The packaged default is an importer-generated Material Symbols Outline Rounded
catalog. It is shipped under package resources with its source identity and
Apache-2.0 notice, and exposes both `material:` and `material-symbols:`. Its
exact subset, generated identity, names, count, bytes, and 13px visual evidence
are release-gated rather than assumed by this specification. No Context means
no catalog and therefore no icon use.

An Iconify alias without geometry overrides is recorded as an alias mapping and
resolves to its canonical entry before Layout. An alias with flip, rotation, or
viewport overrides is normalized into its own canonical entry at import time;
no transform or alias lookup reaches Layout, Scene, or an adapter. Duplicate,
cyclic, or unknown alias targets reject the complete collection.

## 3. Closed vector normalization

The importer accepts only Iconify collection data and only monochrome artwork.
It parses a bounded SVG fragment once, then discards XML. It admits `svg`, `g`,
`path`, `circle`, `rect`, `ellipse`, `line`, `polyline`, and `polygon`; fixed
Iconify flip/rotation metadata; and inherited `fill`, `stroke`, `stroke-width`,
`stroke-linecap`, and `stroke-linejoin` values restricted to `currentColor` or
`none`. It lowers groups, basic shapes, arcs, cubic/smooth commands, and
relative coordinates into finite absolute `move`, `line`, `quadratic`, and
`close` commands using a pinned, versioned geometric tolerance.

Every normalized path has exactly one paint mode:

- `fill`; or
- `stroke`, with finite positive source-unit width and closed
  `butt|round|square` cap plus `miter|round|bevel` join.

Layout applies the uniform viewport scale to path coordinates and stroke width
and returns target-independent completed geometry before Scene construction.
The owning Theme/Colour Scheme supplies the resolved paint colour through
`ScenePaintResolver`; asset source never supplies a literal color for catalog
icons. Scene does not transform paths or scale widths.

The importer rejects `style`, class, transform in SVG body, opacity, literal
colour, gradient, filter, mask, clip, image, text, `use`, `defs`, URL, external
reference, script/event/foreign content, unsupported element, non-finite value,
or any configured depth/path/command/coordinate/tolerance limit. A future
multicolour logo or image belongs to a separately designed asset family; §7
records the one narrow exception #465 makes to that boundary.

## 4. Context closure and public authoring

`chrona/render-context/v0.11` replaces one `inputs.iconCatalog` with
`inputs.iconCatalogs`: a non-empty set of independently pinned catalog
references. Closure resolution verifies every catalog identity and every
declared raster asset before View/Theme/Layout. Materialization copies exactly
those catalog documents and assets under their immutable revisions; no directory
scan or source collection read occurs.

Draft `chrona render` and guided draft resolution accept repeatable explicit
`--icon-catalog PATH` input. Draft derives identities from exactly those files;
the public command never discovers a catalog. Schema descriptions, command help,
examples, and diagnostics document every user-authored catalog and visual field.

## 5. Visual request and Layout composition

`chrona/view/v0.12` contains closed `visuals` requests. Each request targets an
existing presentation label or mark and has either a direct `ref: set:name` or
a field encoding `{field, domain: {value: set:name}, unknown: reject}`. It has
`side: leading|trailing` (default leading) and `decorative: boolean`. A target
allows at most one visual per side. Theme never names an icon.

The successor vocabulary admits all current text placements: document title,
table column header, member/plot label, group header/detail, annotation text,
project note/note index, legend label, summary header/metric/caption, milestone
digest entry, axis label, and as-of label. Existing mark targets admit one icon
per declared object/semantic mark. Each target form has a typed selector and
source-existence validation; a form is not present in the schema until its
Layout projection exists. This prohibits valid-but-unreachable declarations.
For generated lanes, an object-targeted plot-label or semantic-mark visual
applies to every matching selected projection occurrence, with a separate
placement identity per occurrence. A target matching none, or a duplicate
side on one occurrence, fails. Automatic and explicit rows are unchanged.

Layout receives resolved visual requests and normalized assets. For a text
placement it computes each visual's block size as:

```text
typography.fontSize × Theme iconScale(role)
```

and its gap as `fontSize × Theme iconGap(role)`. Scale and gap are finite,
non-negative ratio tokens, not pixels. A successor font-metrics resource must
supply exact cap height; Layout centres the visual on the label cap-height, not
the line box. A mark uses its named mark block metric and the same aspect-ratio
rule. Layout reserves leading and trailing advances before text measurement,
wrapping, ellipsizing, and overflow. It records visual bounds, completed stroke
scale, text bounds/baseline/lines, and logical reading order.

Leading label visuals inherit the completed label paint. Mark visuals use their
own semantic mark role. These are distinct semantic bindings, so Theme can
change appearance without selecting asset or occurrence.

## 6. Scene, accessibility, and targets

`Icon` remains a dedicated Scene primitive. It carries one Layout-completed
vector path list or one verified PNG payload, complete bounds and paint/strokes,
asset identity, alternative, decorative state, visual order, source reference,
and binding pointer. It carries no catalog lookup, raw XML, Theme object, font
metric, text measurement, or coordinate policy. Scene does not derive path
coordinates or stroke scale.

Decorative visuals beside present text are hidden from the accessibility tree.
Meaningful visual use requires a non-empty catalog alternative and an equivalent
existing textual semantic source. Meaningful icon contrast is validated against
its resolved adjacent surface; no icon-only distinction is accepted.

Exact `v0.7-svg` and `v0.7-png` profiles admit normalized vector and verified
raster icons. SVG serializes completed paths/data payloads; PNG is derived from
that complete SVG through the pinned resvg route. PDF, Typst, and TikZ remain
rejection-only until independently designed and evidenced. Neither adapter
selects a fallback, imports a catalog, reopens a path, or decides omission.

## 7. Container artwork exception (#465)

A normalized `chrona/icon-catalog/v0.3` raster PNG entry (§2's "optional
identity-closed purpose-built PNG entry bytes") MAY additionally serve as
the backdrop artwork for a Theme `annotationContainer` binding
(Specification 07, `outline: image`). This is the one narrow exception to
this specification's "does not own... arbitrary images/artwork" boundary:
the entry's identity, licence, and closure discipline are unchanged, and
the same `set:name` reference form is reused, but the *consumer* differs.

- **View still cannot bind a container.** A View's `visuals` grammar
  resolves the same catalog entry only as an ordinary icon (a companion
  beside a label or over a mark, with its own alternative text and
  decorative/meaningful classification). Binding an entry as container
  artwork happens only through the Theme's `annotationContainer.image`
  field, naming the same `<set>:<name>` reference; nothing about the entry
  itself marks it as "container-only" or "icon-only" — the two are
  independent selections of the same closed asset, one by View, one by
  Theme, exactly as an ordinary icon reference is independent of any other
  View field that might name the same entry.
- **A vector glyph is a container backdrop too (#848).** A normalized catalogue **glyph** (§8) MAY be the backdrop artwork of a rectangle `annotationContainer` through the Theme property `artwork` (Specification 07), nine-slice stretched by Layout over the container's paint box. The glyph contributes only its viewport and parts; the fixed borders and the unit are Theme facts, the ink is each layer's selected Theme role (default `annotation-artwork`), and the packaged `chrona-target-parts` entries (`scroll-frame`, `clipping-edge`, `panel-corner`, ...) are usable as they are, with no catalogue edit. A View still cannot select it. The additive `chrona-annotation-parts` catalogue supplies independent `scroll-mounting` and `scroll-rods` layers. It is explicitly pinned through the existing `iconCatalogs` closure, not discovered. Published target-parts resource bytes and identities remain unchanged; a later catalogue is a new id and set pin, never an in-place content edit (#718 design section 6).
- **Nine-slice and content insets are Theme facts, not catalog facts.** The
  entry contributes only its identity, pixel viewport, and PNG payload,
  exactly as it does for an icon. `sliceInsetsEm` and `contentInsetEm` are
  declared on the Theme binding (Specification 07), not on the catalog
  entry, so the same artwork could in principle be bound with different
  insets by different Themes.
- **Arbitrary artwork otherwise stays excluded.** This exception widens
  *use* of an already-admitted PNG entry; it does not widen §2's or §3's
  ingestion rules. A new PNG entry for container use is imported and
  licensed exactly as any other purpose-built PNG entry is today — no new
  import path, catalog resource kind, or Context input is introduced.

## 8. Theme glyph and pattern assets (#496 successor)

The v0.5 asset catalogue retains resource kind `icon-catalog`, Context input
`iconCatalogs`, catalogue set names, `set:name` references, and the existing
identity/notice closure. It adds closed `glyphs` and `patterns` entry maps;
the independent icon-only v0.3 contract is not reinterpreted. All entries share
catalogue provenance with a declared SPDX identifier and complete notice.
Declarative sources use `chrona/theme-asset-source/v0.2`; the normalization
profile is `chrona/theme-asset-normalization/v0.2`. A glyph
viewport side is an integer from 1 through 4096; a glyph has 1–32 normalized
paths, each no longer than 65,536 characters. A pattern tile side is 1–256
units and contains 1–64 ordered primitives. Coordinates are finite and within
the tile; out-of-range input rejects rather than clips or repairs.

A glyph is the normalized #464 multi-part glyph representation: positive
viewport, ordered closed path parts, `fill|stroke` mode, and no fixed color.
Theme may select it for the existing milestone/gate symbol roles. Theme owns
role paint and variant choice; the existing mark-fit logic consumes resolved
parts and Layout completes the mark geometry.
For a catalogue stroke part, its source-unit `strokeWidth` scales by the same
uniform mark-fit factor as its path. Its `lineCap` and `lineJoin` remain exact.
These three values are geometry, not Theme color; Theme supplies the role's
stroke color, without requiring a redundant role `strokeWidth`. Layout carries
the completed width/finish through lane footprints and Scene projection.
Inline #464 glyphs retain their existing Theme-width behavior.

An actually filled point glyph may additionally carry the concrete role's
declared outline (Specification 07, #1287). Layout completes the boundary of
the nonzero-filled union, not the separate part traces, before lane footprints
and legend projection. Original catalogue parts, source-unit stroke finishes,
and semantic ports are unchanged. The additional part uses the role width;
Scene supplies its ink and adapters serialize its completed geometry. This
does not apply to annotation artwork, stamps, or other non-point consumers.

A pattern is a finite repeat tile with positive dimensions, an angle in
`[0,360)` clockwise about tile center, and an ordered list of at most 64
bounded primitives: circles, filled rectangles and stroked lines/arcs. A circle
has `fillChannel: ink | substrate | none` (omitted: `ink`) and an optional
positive ink `strokeWidth`. `none` requires a stroke. Within a circle, fill
precedes stroke; the primitive list is painter order. Circle centres satisfy
the existing tile bounds, but radii and strokes may cross tile edges. Arc
input is approximated by quadratic segments with maximum 0.001 tile-unit
deviation, then discarded. One basis point is 0.01%. The importer counts
final visible ink at centres on a fixed 128×128 grid in the tile-local cell.
Clip each tile's primitive stack to that tile before repetition; neighbouring
tile translations do not contribute to its density. For density only, each normalized quadratic
is expanded to exactly 16
equal-parameter chords; straight commands remain straight. Source lines and
arcs use round caps and joins. A center is covered by a stroke when its
distance to any chord is at most half the stroke width; circle boundaries are
included and rectangles include left/top but exclude right/bottom. At each
centre, an ink operation sets coverage and a substrate operation clears it;
`none` performs no fill. Circle strokes cover radial distances from
`max(0,radius-strokeWidth/2)` through `radius+strokeWidth/2`, inclusively.
Clockwise rotation applies to both the tile geometry and this fundamental
cell for rendering, so intrinsic `densityBasisPoints` is invariant to angle;
sampling an unrotated axis-aligned viewport instead is not equivalent.
The fixed chords define density measurement only: Scene and adapters retain
the normalized quadratic geometry. Its required `densityBasisPoints` field is
an integer from 1 through 10,000 and must equal the final ink fraction rounded
half-up to the nearest basis point. A zero-ink result refuses normalization as
`E_THEME_ASSET_SOURCE_DENSITY`, even if positive density was declared.
Thus the starter's 12.5% dither uses 1,250 basis
points exactly; it is never rounded to a whole percent. Stroke widths are finite,
positive, and at most 16 units. It has no paint, target syntax, executable
content, or arbitrary transform data. Theme's existing role `pattern`
property names a typed pattern token whose value is
`{kind: catalog, ref: set:name}` on one of the exact registered role/property
pairs in Specification 07. Theme `fill` is the opaque substrate and Theme
`stroke` is opaque ink; opaque pattern roles require opacity 1.0. A substrate
operation requires that completed opaque fill; ink-only surface patterns
cannot contain one and refuse paint completion as `E_PRESENTATION_PAINT_INVALID`.
Per-primitive colours and opacity are not admitted. Catalogue
references resolve after Theme inheritance
and before Layout; unknown set/name or wrong entry kind reports the exact Theme
pointer and authored `set:name`.

Current authored Theme v0.15 and derived Theme v0.16 carry catalog glyph
references and catalog-valued pattern tokens. Layout owns repeated-region
bounds, clipping, and tile origin. Scene v0.7 extends the completed pattern
value with normalized tile primitives, angle, density, tile origin, and clip
bounds. `ScenePaint.fill` is the substrate and `ScenePaint.stroke` is the ink;
PatternGeometry carries no colors. Scene does not read catalogue or Theme
resources. Optional circle channel/width fields are completed geometry;
their absence preserves filled-ink circles. No normalization-profile field or
second density field is added to Scene. An adapter may serialize repetition using target-native
syntax, but the completed tile, angle, origin, and clip bounds determine it.
Contrast evaluates substrate against the actual host ground and ink against
both substrate and host ground. The lowest applicable ratio must meet the
semantic floor: 3.0:1 for mark roles (an error below it), 1.10:1 for decoration
roles (a warning below it, Specification 46 section 8). All
channels are opaque under the existing representative-ground contract.
Opaque patterned hosts retain conservative two-colour contrast even when some
ink is occluded; positive post-composition density proves surviving ink.
Fill-less surface patterns use actual sparse-ink contact (Spec 46); substrate
operations are never admitted to that path. No contrast floor is weakened.
Perceptibility inspection receives the same channels and tile/density facts;
neither gate infers color from a catalogue. SVG serializes completed geometry;
PNG is generated from that SVG by the pinned resvg route. Other targets reject
these bindings until separately profiled. Import accepts declarative YAML with
explicit SPDX and notice, validates the whole input, and emits canonical
catalogue bytes atomically. No raw SVG reaches rendering; a source SVG importer
is deferred.

Render Context keeps its current schema because its `iconCatalogs` field and
reference shape do not change; closure resolution is extended to validate and
pin catalogue v0.5. The existing presentation-preset v0.1 already pins
`iconCatalogs` and an optional detail profile. Builtin-library v0.2 adds catalogue members. Copy
preserves exact catalogue bytes and notices and writes
their pinned references into the preset; `render --preset` uses that closure.
This does not define package acquisition. Spec 62 may admit v0.5 as an
ordinary verified static asset member under its existing package boundary.

**Migration (#849).** Source v0.1/catalogue v0.4 use periodic-union density,
which differs at tile edges and cannot represent knockouts. Retire their live
authoring readers after atomically migrating first-party resources and pins to
v0.2/v0.5; do not silently reinterpret them or infer a legacy mode from field
absence. Publish successor source/catalogue/manifest identities, never overwrite
an immutable published asset. Keep the independently supported Material
icon-only v0.3 catalogue unchanged. The fifteen existing packaged patterns
retain their density under the corrected rule; this is not a compatibility
promise for arbitrary old boundary-crossing tiles.

## 9. Acceptance and evolution

Release evidence must include real Material Symbols, Lucide, and Tabler import
fixtures; a packaged Material default; user-owned import; direct and encoded
selection; every label target; leading/trailing wrapping and overflow; fill and
stroke serialization; cap-height placement; label/mark paint separation;
decorative/meaningful accessibility; exact rejection diagnostics; PNG decoded
pixel checks; bounded raster artifact size; materialized closure; full tests,
conformance, wheel smoke, and Ubuntu/macOS CI.

Any omission, rejected requirement, or future icon/image capability is recorded
against R350-01 through R350-12 in the issue and release review before closure.
