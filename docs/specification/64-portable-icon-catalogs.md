# Portable Icon Catalogs and Immutable Visual Assets

**Status:** Proposed
**Depends on:** [07 Style and Theme](07-style-and-theme.md),
[08 Scene and Rendering](08-scene-and-rendering.md),
[12 Quality and Invariants](12-quality-and-invariants.md),
[13 Presentation Format](13-presentation-format.md),
[33 Intent-Oriented Layout](33-intent-oriented-layout.md),
[50 Constraint-Driven Gantt Surface Quality](50-constraint-driven-gantt-surface-quality.md),
[55 Presentation Design Space](55-presentation-design-space.md),
[62 Declarative Presentation Packages](62-declarative-presentation-packages.md), and
[63 Portable Visual Capabilities](63-portable-visual-capabilities.md).
**Owns:** closed icon-catalog resources, SVG/PNG icon ingestion and asset closure,
renderer-neutral icon primitive data, icon accessibility, and icon target capability.
It does not own generic images, arbitrary SVG/CSS/XML, semantic facts, text
measurement, concrete colour literals, package acquisition, or target fallback.

## 1. Contract

An icon is a bounded visual representation of an existing semantic role. It can be a
leading element of a text label or a semantic mark; it never creates a new Project
meaning and must not be the only representation of required meaning.

```text
icon-catalog + Context closure + View/semantic icon binding + Theme treatment
  -> Layout measured icon/text or icon mark placement
  -> completed Scene Icon primitive
  -> exact target-profile serialization
```

The only accepted asset classes in v0.1 are local `vector` SVG and local `raster` PNG.
Both are acquired from the already selected immutable Store snapshot, verified by SHA-256,
and copied into a materialized closure. A host path is a locator only. A renderer receives
neither a path nor raw source SVG; it cannot reopen, substitute, recolour, resize, or
choose an asset.

## 2. Catalog resource and asset closure

`chrona/icon-catalog/v0.1` is an ordinary typed resource with stable resource ID and
closed entries. A Context has at most one optional `inputs.iconCatalog` typed reference.
Its namespaced icon IDs are canonical map keys; duplicate/reordered spellings are
structurally impossible and canonical evidence orders entries lexically by ID.

```yaml
version: chrona/icon-catalog/v0.1
kind: icon-catalog
id: acme-review-icons
body:
  icons:
    acme.risk:
      kind: vector
      source: {address: assets/risk.svg, contentIdentity: sha256:...}
      viewport: {inlineSize: 24, blockSize: 24}
      alternative: Risk requires attention
    acme.approved-logo:
      kind: raster
      source: {address: assets/approved.png, contentIdentity: sha256:...}
      viewport: {inlineSize: 96, blockSize: 96}
      alternative: Approved programme mark
```

An asset address is a non-empty Store-relative POSIX address with no `.` or `..` segment,
symlink traversal, URL scheme, fragment, query, data URI, or ambient directory search.
The loader reads exact bytes from the Context resource's immutable revision, verifies the
declared SHA-256 before interpretation, and records the catalog identity plus every
referenced asset identity in ordered closure evidence. Materialization copies the catalog
document and each verified asset under that immutable revision. Mutation, absence,
identity mismatch, unsafe path, duplicate ID, or unsupported source class fails before
Layout.

Package members may include an already-approved catalog and its static assets only after
the package acquisition contract of Specification 62 exists. A package cannot add an
icon vocabulary, source kind, or dynamic resolver.

## 3. Bounded normalization

### 3.1 Vector SVG

The loader parses vector SVG once and normalizes it to an immutable, renderer-neutral
payload. It accepts a root `svg`, nested `g`, and paint-free `path` elements only. It
accepts finite numeric viewbox values and the path commands `M`, `L`, `H`, `V`, `Q`, `C`,
and `Z` (absolute or relative, normalized to absolute coordinates). It rejects arcs,
transform, style/class, inherited presentation attributes, stroke, fill, opacity, IDs,
`use`, external references, image, text, script, event attributes, `foreignObject`,
filter, mask, clip, animation, CSS, URL-valued attributes, and every element or attribute
outside this closed set. The normalizer bounds command count, nesting, coordinate magnitude,
and viewport dimensions with named diagnostics.

The normalized payload consists of one finite positive viewport and ordered fill paths.
Its colours are not asset authority: Theme/Color Scheme resolves the completed icon paint.
The raw SVG never crosses the loader boundary and is retained only as immutable closure
evidence for audit/re-materialization.

### 3.2 Raster PNG

The loader accepts only PNG signature/IHDR-valid bytes with a finite positive intrinsic
width and height within declared limits. It verifies that the catalog viewport matches the
intrinsic dimensions (or an explicitly specified deterministic normalization rule), and
does not decode metadata as policy. The original verified PNG bytes are preserved as the
raster payload, carried by content identity, and encoded by the SVG/PNG route without a
filesystem reference. No EXIF, URL, animation, embedded profile, or alternate image
format is admitted in v0.1.

## 4. Layout, semantic, and Scene boundary

The semantic/View layer chooses an existing source's namespaced catalog ID and whether it
emits `leading-label-icon`, `mark-icon`, or no icon. The first closed View syntax is
`body.iconBindings`, whose entries uniquely name `{source: {kind, id}, placement:
leading-label|mark, icon: acme.risk, decorative: boolean}`. `source` identifies an
already selected semantic object, View annotation, group, or existing semantic mark; it
does not introduce a coordinate, match by title, or mutate semantic truth. A binding to an
absent source or an unavailable label/mark placement diagnoses. Theme maps that role only
to tokenized size, gap, paint, and finish treatment. The binding is validated against the
resolved catalog before measurement. Theme cannot name an asset source, raw geometry,
concrete colour literal, semantic icon selection, target profile, or fallback.

For a leading label, Layout consumes the normalized intrinsic viewport, resolved icon size,
gap, typography, text, and available inline width. It emits a single placement containing
icon bounds, text bounds, text baseline/lines/font identity, gap, visual order, source
identity, alternative, and overflow result. The icon occupies inline space before text;
wrapping and ellipsizing operate on the remaining measured text interval. For a mark,
Layout emits icon bounds, scale, and completed anchor/port relation. Scene only projects
those placements.

`Icon` is a new Scene primitive kind. It is not `Symbol`, because Symbols retain their
closed geometric semantic vocabulary; it is not `Path`, because a Path is general surface
geometry and carries no asset identity/alternative. An Icon primitive has exactly one
normalized vector payload or one immutable raster identity/payload, complete bounds,
resolved paint where applicable, `decorative` flag, alternative, visual role, source
reference, and stable Scene identity. It has no catalog ID lookup, authored Theme, file
path, text measurement, or placement policy. Vector coordinates are transformed by Scene
only from already completed bounds; adapters serialize them verbatim.

## 5. Accessibility, profiles, and diagnostics

A decorative icon has an empty alternative and is hidden from the target accessibility
tree. A non-decorative icon has a non-empty catalog alternative and an equivalent existing
textual role/source; a required semantic distinction cannot be icon-only. Leading icons are
normally decorative because the label remains present. The SVG adapter emits an accessible
name only for non-decorative icons; PNG preserves the same Scene/accessibility evidence in
the manifest. Adapters never invent alternative text.

The v0.1 required capability IDs are `icon.vector` and `icon.raster`. A Context names one
complete target profile, not independently combinable visual and icon profiles. The
successor profiles are `chrona-output/visual/v0.7-svg` and
`chrona-output/visual/v0.7-png`, each extending the matching v0.6 target profile with
both icon IDs. `chrona-output/visual/v0.7-pdf` is admitted only if characterization proves
that the existing SVG-derived PDF path preserves both normalized vectors and immutable PNG
payloads; it may deliberately admit the icon IDs while continuing to reject #349's
drop-shadow capability. Until that evidence exists, PDF has no v0.7 profile. Typst and
TikZ remain baseline-only. Unsupported required use fails before rendering; decorative
omission is a Scene-resolution policy only when the exact profile explicitly permits it.
The adapter does not silently omit, rasterize, or substitute an icon.

Stable diagnostics include `E_ICON_CATALOG_SCHEMA`, `E_ICON_ASSET_PATH`,
`E_ICON_ASSET_IDENTITY`, `E_ICON_ASSET_MISSING`, `E_ICON_SVG_UNSAFE`,
`E_ICON_SVG_LIMIT`, `E_ICON_PNG_INVALID`, `E_ICON_PNG_LIMIT`,
`E_ICON_BINDING`, `E_ICON_ACCESSIBILITY`, and `E_ICON_CAPABILITY_UNSUPPORTED`.
Each identifies the resource/entry/property pointer. A malformed or hostile asset is
rejected at closure ingress, never passed to a renderer.

## 6. Deliberate exclusions and evolution

This specification is a narrow closed-asset exception to Specification 63's generic image
deferral. It does not admit a general Image primitive, arbitrary artwork, bitmap/photo
placement, SVG styling, gradients in assets, external icon packages, custom fonts, network
fetches, or profile claims for PDF/Typst/TikZ. A later asset class, SVG element/attribute,
Scene payload, icon-only semantic, generic image, package route, or target requires a new
versioned profile plus evidence and this specification's architecture review.

Design Space may expose a named icon treatment only when it resolves to the existing
View/semantic icon binding and Theme treatment above. It may not expose a raw asset
picker, coordinate, or renderer feature. The resulting catalog remains an ordinary
explicit resource, so a user can fork/edit it under the same immutable closure rules.
