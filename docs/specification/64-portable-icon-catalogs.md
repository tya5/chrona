# Portable Icon Catalogs and Immutable Visual Assets

**Status:** Implemented — v0.3 successor contract
**Owns:** local Iconify collection ingestion, normalized monochrome icon
catalogs, catalog-set closure, label/mark visual selection, completed Icon
primitives, icon accessibility, and SVG/PNG target capability.
**Does not own:** Project facts, arbitrary images/artwork, raw SVG at render
time, concrete colours, Layout coordinates, package acquisition, network
fetching, target fallback, or PDF rich-paint fidelity.

## 1. Contract and authority

```text
local Iconify JSON -> normalized catalog -> pinned Context catalog set
  + View visual request + Theme/Colour Scheme + Font metrics
  -> Layout visual/text placement -> completed Scene Icon -> adapter
```

An icon is a visual companion to an existing textual or semantic source. It
cannot be the only carrier of required meaning. View owns occurrence, catalog
reference, side, and field-to-icon mapping; Theme owns size ratio, gap ratio,
and visual paint; Layout owns all sizing, cap-height alignment, measurement,
wrapping, overflow, and reading order; Scene owns completed primitives; an
adapter serializes only completed data.

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

At Layout/Scene completion a uniform viewport scale transforms stroke width to
target-independent completed geometry. The owning Theme/Colour Scheme supplies
the resolved paint colour; asset source never supplies a literal colour.

The importer rejects `style`, class, transform in SVG body, opacity, literal
colour, gradient, filter, mask, clip, image, text, `use`, `defs`, URL, external
reference, script/event/foreign content, unsupported element, non-finite value,
or any configured depth/path/command/coordinate/tolerance limit. A future
multicolour logo or image belongs to a separately designed asset family.

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

`Icon` remains a dedicated Scene primitive. It carries one normalized vector
path list or one verified PNG payload, complete bounds, complete paint/strokes,
asset identity, alternative, decorative state, visual order, source reference,
and binding pointer. It carries no catalog lookup, raw XML, Theme object, font
metric, text measurement, or coordinate policy.

Decorative visuals beside present text are hidden from the accessibility tree.
Meaningful visual use requires a non-empty catalog alternative and an equivalent
existing textual semantic source. Meaningful icon contrast is validated against
its resolved adjacent surface; no icon-only distinction is accepted.

Exact `v0.7-svg` and `v0.7-png` profiles admit normalized vector and verified
raster icons. SVG serializes completed paths/data payloads; PNG is derived from
that complete SVG through the pinned resvg route. PDF, Typst, and TikZ remain
rejection-only until independently designed and evidenced. Neither adapter
selects a fallback, imports a catalog, reopens a path, or decides omission.

## 7. Acceptance and evolution

Release evidence must include real Material Symbols, Lucide, and Tabler import
fixtures; a packaged Material default; user-owned import; direct and encoded
selection; every label target; leading/trailing wrapping and overflow; fill and
stroke serialization; cap-height placement; label/mark paint separation;
decorative/meaningful accessibility; exact rejection diagnostics; PNG decoded
pixel checks; bounded raster artifact size; materialized closure; full tests,
conformance, wheel smoke, and Ubuntu/macOS CI.

Any omission, rejected requirement, or future icon/image capability is recorded
against R350-01 through R350-12 in the issue and release review before closure.
