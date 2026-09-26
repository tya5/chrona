# Container Image Assets

**Status:** Proposed — pending architecture review ([#465](../design/issue-465-image-annotation-container-design-2026-09-27.md))
**Owns:** normalized nine-slice-stretchable raster artwork used as an
annotation container backdrop, its catalog identity and closure, and the
completed per-tile source/destination geometry a Theme binding resolves to.
**Does not own:** Project facts, View authoring (a View cannot select this
asset kind — see Specification 64 for the visual-companion pathway a View
does own), icon accessibility semantics (alternative text, decorative/
meaningful classification), photographic or third-party artwork ingestion
(no import command exists yet; see the design's asset-provenance risk),
concrete colours beyond the artwork's own printed pixels, Layout coordinates,
or PDF/Typst/TikZ fidelity.

## 1. Contract and authority

```text
local PNG artwork -> normalized container-image catalog -> pinned Context
  catalog set + Theme annotationContainer(outline: image) binding
  -> Layout content box / nine-slice tile geometry -> completed Scene paint
  -> adapter
```

Specification 64 ("Portable Icon Catalogs") explicitly excludes "arbitrary
images/artwork" and ends: "a future multicolour logo or image belongs to a
separately designed asset family." This specification is that family. It
deliberately does **not** extend `chrona/icon-catalog/v0.3`: an icon is a
visual companion a View selects beside text or over one mark, with its own
accessibility contract; a container image is structural chrome only a Theme
may bind to an annotation box role (#465 acceptance: "A View cannot"). Using
one resource kind for both would let a View's `visuals` grammar reach
content it must never select. The two families share only their
engineering pattern (content identity, closure, immutable revision), not
their resource kind, schema, or accessibility rules.

## 2. Normalized catalog document

`chrona/container-image-catalog/v0.1` stores canonical normalized entries:

- one canonical `prefix`, source identity, and SHA-256 content identity per
  entry;
- declared license identifier and complete local notice text/provenance —
  the same discipline Specification 64 §2 requires, because a shipped
  catalog document still carries someone's artwork and its licence;
- a pixel `viewport` (`inlineSize`, `blockSize`) and one verified PNG
  payload, addressed relative to the catalog revision;
- lexically ordered canonical entry names; `set:name` is the only authored
  reference form, resolved against a pinned Context catalog set exactly as
  Specification 64 §2 resolves icon references, with the same rejections
  (duplicate prefix/alias, unknown set, unknown name, ambiguous reference).

No importer command exists yet for third-party collections; the packaged
default and any example asset are repository-owned artwork (not
photographic, not a third party's copyrighted work), produced by a
deterministic local script and hand-normalized into this document format.
A future `chrona container-image-catalog import` command, mirroring
Specification 64 §2's ingestion discipline, is out of scope until a concrete
third-party asset need exists.

## 3. Context closure

`chrona/render-context/v0.17` adds an optional, additive
`inputs.containerImageCatalogs`: a non-empty set of independently pinned
catalog references, absent by default. Closure resolution verifies every
declared catalog identity and PNG payload before Theme/Layout, exactly as
`inputs.iconCatalogs` is verified today. A Theme binding that names an asset
outside the pinned closure is a stable ingress error before Layout, never a
silently blank or omitted container.

## 4. Theme binding, Layout, and Scene

A Theme role's `annotationContainer` token (Specification 07,
Theme v0.11) may declare `outline: image`, naming one `set:name` reference
into this family plus a nine-slice `sliceInsetsEm` and a `contentInsetEm`
(both independent, four-sided, em-relative). Layout measures note text into
the content inset's box, expands it by the content inset to the paint box,
and derives up to nine `(source, destination)` tile rects from the paint box
and the stretch insets. Scene carries the completed tile list, the asset
identity, and the artwork's pixel viewport on the annotation box primitive's
paint (an additive `image` fill mode, alongside the existing flat and
gradient fills); it carries no catalog lookup, raw byte decoding policy, or
inset arithmetic beyond what Layout already completed. The role's existing
fill colour binding is the Theme author's declared representative colour
for the artwork's content area, used unchanged by every existing contrast
and perceptibility ground computation — this specification introduces no
new ground-resolution rule.

## 5. Adapters and determinism

Exact `v0.7-svg` and `v0.7-png` profiles (Specification 64 §6) also serve
this family unchanged: SVG embeds each completed tile as one `<image>`
element with the tile's source rect as a cropping viewBox and its
destination rect as absolute geometry (the same base64 embedding raster
icons already use, repeated per tile); PNG is derived from that complete
SVG through the same pinned resvg route. Neither adapter computes a tile
boundary, resolves a catalog reference, or invents a stretch ratio.

## 6. Acceptance and evolution

Release evidence must include: the normalized catalog document and its
closure round-trip; a Theme `outline: image` binding rendering identically
across two runs (deterministic tiling); a Theme without the binding
rendering byte-identical to its pre-#465 output; contrast and
perceptibility evidence treating the declared fill as the note's ground;
and one committed public slide. A shared container across several
annotations (Tenth Frame's strip), rotation (Marquee's tilted clippings),
and a generalized third-party import command are named, deliberately
deferred gaps, not silently absorbed into this contract.
