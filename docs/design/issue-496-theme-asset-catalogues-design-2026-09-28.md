# #496 Theme asset catalogues design

**Status:** Design complete; implementation plan follows.
**Plan:** [#496 work record](../planning/active/issue-496-theme-asset-catalogues-work-record-2026-09-28.md).
**Review:** [whole-architecture review](../reviews/current/issue-496-theme-asset-catalogues-architecture-review-2026-09-28.md).
**Normative contracts:** [Spec 64](../specification/64-portable-icon-catalogs.md), [Spec 07](../specification/07-style-and-theme.md), [Spec 08](../specification/08-scene-and-rendering.md), [Spec 62](../specification/62-declarative-presentation-packages.md).

## Selected behavior

Extend the existing licensed `icon-catalog` resource and `iconCatalogs`
Context closure rather than introducing another resource family. Catalogue
v0.4 adds normalized glyph and pattern entries while retaining icon entries,
`set:name`, catalogue identity, and notice closure. v0.3 is migrated
explicitly; there is no silent version reinterpretation.

Theme v0.13 may bind a catalogue glyph through the existing symbol treatment
for milestone/gate marks. The glyph contains ordered normalized paths and
paint modes, never literal colors; Theme supplies role paint and #464 mark-fit
behavior remains authoritative. Derived Theme advances from v0.12 to v0.14.
Inline glyphs remain a migration form.

Catalog patterns are named through the existing `pattern` role property and
a typed pattern token `{kind: catalog, ref: set:name}`. The exact admitted
role/property pairs and the normalized tile, angle, arc, and density rules are
defined in Specifications 07 and 64. The role's Theme fill is opaque substrate
and stroke is opaque ink; pattern-role opacity is 1.0. No color or target
syntax is stored in the asset.

The coordinator resolves and validates catalogue references after Theme
inheritance and before Layout. Layout owns region bounds, clip bounds, and
tile origin. Scene v0.7 carries normalized tile primitives, angle, density,
origin, clipping, and completed paint. Adapters can express fixed periodic
repetition in target syntax but cannot alter those values. SVG is the authored
target and PNG uses the pinned SVG-to-resvg route. Contrast checks substrate
against host and ink against substrate and host using the existing semantic
floor; perceptibility receives the same resolved channels and geometry.

Keep `presentation-preset/v0.1`, which already pins catalogues and detail
profiles. Advance the builtin preset library to v0.2 for catalogue members.
Copy writes the exact catalogue and notice and includes its pinned reference;
`render --preset` consumes the same closure. The starter catalogue contains
the seven named glyphs and six pattern entries (three ordered-dither densities
count separately). A generic preset uses a glyph, a pattern, and its existing
review-detail legend. Spec 62 remains proposed; no package resolver is part of
this design.

## Ingress and failures

One local declarative YAML source imports glyph/pattern entries with explicit
SPDX and complete notice. It validates the complete source and emits canonical
catalogue bytes atomically. The optional SVG-subset importer is deferred. Raw
SVG at render time, CSS, filters, gradients, network lookup, arbitrary image
ingress, and new raster entry kinds are excluded; #465 PNG container art
continues unchanged.

Unknown set/name, wrong entry kind, invalid normalized data, duplicate
namespace, and absent licensing notice fail before Layout. A missing Theme
reference reports `E_THEME_ASSET_REFERENCE` at its exact Theme property and
includes the authored `set:name`. Copy refuses a nonempty output directory and
copies only declared members. Context/preset closure verifies exact identities
without scans or network access.

## Migration and successor work

The resource migrations are catalogue v0.3→v0.4 and preset-library
v0.1→v0.2. Context fields remain unchanged; its resolver must admit and pin
catalogue v0.4. Theme v0.11/v0.12 remain valid; v0.13/v0.14 carry the new
authoring/inheritance forms. Scene v0.6 remains unchanged; v0.7 carries the
completed pattern value. Existing flat fills, inline glyphs, and #465 PNG
payloads/insets retain their behavior.

The implementation plan must name schema/registry mirrors, import and closure
owners, starter asset provenance/notices, preset copy/materializer changes,
focused tests, rendered SVG/PNG comparisons, and contrast/perceptibility
evidence before product code changes.
