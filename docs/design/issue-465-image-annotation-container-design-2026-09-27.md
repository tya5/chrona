# Design — Image-Backed Annotation Container (#465)

**Plan:** [design plan](../planning/active/issue-465-image-annotation-container-design-plan-2026-09-27.md).
**Builds on:** #466 C2's `annotationContainer` token and balloon geometry
(`5b96ee50`); does not change #466/#467's placement or lane design.

## Use cases

The same Theme `annotationContainer` binding that today chooses `rectangle`
or `balloon` gains a third outline, `image`: a nine-slice-stretched raster
backdrop behind the note's text, with a declared content inset that tells
Layout where the text goes. A View never names the image; it only ever
authors the note's text/anchor/candidates, exactly as today. A Theme without
the binding is untouched — same rectangle bytes as before #466 and #465
both. The mechanism must serve all four approved targets that draw a note
over a framed image (Yuya's scroll, Tenth Frame's photo-booth frame,
Marquee's clipping, Off-World's printout) as one contract, not a per-theme
special case.

## Contract 1: a new sibling asset family (Specification 65 draft)

Icon catalogs (specification 64) are closed to "arbitrary images/artwork" by
their own stated boundary, and end with "a future multicolour logo or image
belongs to a separately designed asset family." This design proposes that
family as `chrona/container-image-catalog/v0.1`, mirroring spec 64's identity
and closure engineering without inheriting its icon-specific accessibility
contract (alternative text, decorative/meaningful classification) or its
monochrome vector normalization:

- one canonical normalized entry per `name`: SHA-256 content identity,
  declared license identifier and notice text/provenance (same discipline as
  spec 64 §2), pixel `viewport` (`inlineSize`, `blockSize`), and one verified
  PNG payload;
- `set:name` addressing, resolved against a pinned Context catalog set —
  the same grammar spec 64 uses for icons, but a distinct resource kind, so
  a View's `visuals` grammar (which only resolves icon catalogs) cannot
  reach a container-image entry; acceptance bullet 1 ("A View cannot")
  holds by construction, not by a runtime check;
- `chrona/render-context/v0.17` adds an optional, additive
  `inputs.containerImageCatalogs` (a non-empty set of pinned catalog
  references, absent by default) alongside `inputs.iconCatalogs`. Closure
  resolution verifies every declared catalog identity and PNG payload before
  Theme/Layout, exactly as icon catalogs are verified today. No Context
  input is required unless a Theme actually declares an `outline: image`
  binding.
- no generalized third-party import command in this slice (see design
  plan's asset-provenance risk): the one committed asset is repository-owned
  artwork (a bordered nine-slice test panel, not photographic content),
  produced by a small deterministic script under `tools/`, hand-normalized
  into the catalog document format above. A `chrona container-image-catalog
  import` command mirroring spec 64's importer is named as a follow-up, not
  built now, because nothing in the literal acceptance requires ingesting a
  third party's artwork yet.

This is the one open decision the design plan could not close alone: an
alternative (storing this artwork as an icon-catalog PNG entry and letting
Theme reference it by the same `set:name` used for icons) was rejected
because it would let a View's ordinary `visuals` grammar accidentally select
structural chrome, and because spec 64 explicitly disclaims this content.
The architecture review below records this as a decision needing the lead's
or owner's confirmation before implementation, not a silently chosen path.

## Contract 2: Theme `annotationContainer.image`

Theme v0.11's `annotationContainer` token (schema
`theme-v0.11.schema.yaml`) grows a third finite `outline` value additively:

```yaml
type: annotationContainer
value:
  outline: image
  image: set:name              # container-image-catalog reference
  cornerRadius: 0               # kept for schema symmetry with rectangle/balloon; must be 0 for image
  sliceInsetsEm: {top: 0.9, right: 0.6, bottom: 0.9, left: 0.6}
  contentInsetEm: {top: 1.1, right: 0.8, bottom: 1.1, left: 0.8}
```

- `image` is a catalog reference in the new family (Contract 1); resolved
  before Layout, exactly as an icon `ref` is resolved before Layout (spec 64
  §5) — Theme carries no raw bytes, no path, no viewport math.
- `sliceInsetsEm` (four non-negative em values) declares the nine-slice
  fixed border: each corner tile keeps its authored pixel size scaled by
  the viewport-to-target ratio; each edge tile stretches along one axis;
  the centre tile stretches along both. This is the "stretch rule" the
  issue and every target README ask for (rods keep their size while the
  paper grows).
- `contentInsetEm` (four non-negative em values, independent of
  `sliceInsetsEm`) declares the box Layout measures text into — the paper,
  not the mounting. It is typically inside the stretch insets but the
  schema does not require that relationship; a content inset outside the
  fixed border is a Theme authoring choice, not an error, since some framed
  images (Off-World's printout) may want text closer to the frame's own
  printed margin than its structural border.
- `outline: image` requires all four of `image`, `sliceInsetsEm`,
  `contentInsetEm` and forbids a non-zero `cornerRadius` (an image supplies
  its own corner treatment in the artwork; a Theme cannot ask Layout to
  round a raster). `outline: rectangle`/`balloon` reject these new
  properties, matching the existing `if/then` pattern for `tailBaseEm`.
- `ThemeTokenView.annotation_container` gains a third return shape carrying
  the resolved catalog entry (viewport, payload identity) plus the two
  inset rectangles in em; callers already branch on the first tuple element
  (`outline`), so the branch is additive, not a signature break.
- The role's existing `annotation-box.fill`/`.stroke` colour bindings are
  unchanged and still required; for `outline: image`, `fill` becomes the
  Theme author's *declared representative content-area colour* (see
  Contract 4) rather than a painted rectangle fill. This asks nothing new
  of the colour-binding schema.

## Contract 3: Layout content box, stretch geometry, collision

Today `project_annotation_box` (and `nearest_free_box`/`nearest_free_tail_box`
in `annotation_search.py`) measure the note's text and return the box that
*is* the paint box — zero implicit inset. With a declared `contentInsetEm`,
Layout instead measures text into a **content box** and derives the **paint
box** as the content box expanded by the content inset on every side. The
paint box — not the content box — is what candidate search commits to the
shared `SurfaceObstacleIndex` and what the connector (tail or leader) must
avoid: text wrapping and overflow (#449) work against the content box, but
collision, obstacle registration, and the `annotation-box` obstacle class
(#466) all key off the paint box, exactly as they do today for a plain
rectangle (where content box and paint box already coincide).

Given the paint box and the declared `sliceInsetsEm`, `image_slice_geometry`
(new, parallel to `balloon_outline` in shape and testing style) returns up
to nine `(sourceRect, destinationRect)` tile pairs in absolute Layout
coordinates: four fixed corners, four stretched edges, one stretched centre.
Degenerate declarations collapse tiles exactly like a css nine-slice would
(a stretch inset of `0` on one axis collapses that axis's three tiles into
one full-bleed stretch — the vertical "three-slice" a scroll needs when
only its top/bottom rods are fixed). No image-specific collision math is
added: the paint box is one ordinary rectangle for obstacle purposes,
whether its interior paints a colour or nine image tiles.

## Contract 4: Scene `ScenePaint.image` and adapter parity

`ScenePaint` gains one additive field, parallel to its existing `gradient`:

```python
image: "ImageFill | None" = None

@dataclass(frozen=True)
class ImageFill:
    asset_identity: str
    viewport: tuple[int, int]
    payload: bytes                 # PNG bytes, in-memory only (never serialized)
    tiles: tuple[ImageTile, ...]   # up to 9, each with source+destination rects

@dataclass(frozen=True)
class ImageTile:
    source: tuple[float, float, float, float]        # asset pixel space
    destination: tuple[float, float, float, float]    # surface coordinates
```

The container stays exactly the primitive kind it is today: `Rect` when the
role has no tail, `Symbol` (the existing balloon outline) when it does —
`outline: image` and `outline: balloon` are independent axes (an image
container can still grow a tail if its role also wants one; that tail is
painted as today's outline, with the image tiled inside it). `paint.fill`
keeps carrying the Theme's declared representative colour (Contract 2's
last bullet); `paint.image`, when present, is what adapters actually paint
for the container's interior, on top of `fill`. This choice means:

- `contrast_policy.py`'s `_ground_under` (which already accepts any prior
  `Rect`/`Symbol` with an opaque flat or gradient `fill`) needs **no
  change** — the ground it reports for image-backed note text is exactly
  the declared colour, sourced the same way a plain rectangle's ground is
  sourced today.
- `perceptibility.py`'s `_occlusion_findings` and `_paint_findings` need
  **no change** — they already operate on `kind`/`paint.fill` in a way that
  covers this primitive unchanged.
- Serialization (`scene/serialization.py`) adds one `image` key to `_paint`,
  parallel to the existing `gradient` key: `assetIdentity`, `viewport`,
  and each tile's source/destination rects (no raw bytes — matching how
  `icon.assetIdentity` never carries bytes in committed Scene JSON today).
- The SVG renderer (`renderers/v05_svg.py`) draws each tile as one `<image>`
  element per tile: `href="data:image/png;base64,..."` with the tile's
  `source` rect expressed as a cropping `viewBox`/`preserveAspectRatio="none"`
  and its `destination` rect as `x`/`y`/`width`/`height` — the same
  `b64encode(...)` call already used for raster icons (`v05_svg.py:182-184`),
  repeated per tile instead of once. PNG output stays derived from that
  complete SVG via the pinned resvg route (spec 64 §6); no PNG-specific
  tiling code is written.
- No adapter computes a tile boundary, an inset, or a stretch ratio; every
  number an adapter uses is already resolved by Layout/Scene, matching
  #466's "adapters do not invent a tail" precedent for this new case.

## Why not a dedicated `Image`/`ContainerImage` primitive kind

Considered and rejected in the design plan (U3): a new `kind` would need
`contrast_policy.py` and `perceptibility.py` to learn it explicitly, would
duplicate the `Rect`/`Symbol` paint-role wiring `v05_builder.py` already
does for the annotation box, and would make "one container mechanism" two
mechanisms at the Scene layer even though it is one at the Theme layer. The
`ScenePaint.image` fill mode keeps the container one primitive with one new,
additive way to paint its interior — the same relationship `gradient`
already has to `fill`.

## Migration and compatibility

- Theme v0.11 stays additive: a Theme without `outline: image` is
  byte-identical (acceptance 5); a Theme with `outline: rectangle` or
  `balloon` is unaffected by the new branch.
- `chrona/render-context/v0.17` is additive: `inputs.containerImageCatalogs`
  absent means no such catalog, and a Theme cannot then declare
  `outline: image` (an ingress error, not a silently-skipped container,
  matching #466's "a missing source/slot is an ingress error" precedent).
- No View schema version changes. If implementation later finds a View
  field is unavoidable to express something in this design, that is a stop-
  and-ask event (View v0.26/v0.27 are contended), not a silent addition.

## Diagnostics

- `E_THEME_TOKEN_TYPE` extends to the new `annotationContainer.image`
  sub-shape (missing/invalid `image`, `sliceInsetsEm`, `contentInsetEm`, or
  a non-zero `cornerRadius` with `outline: image`) — reusing the existing
  diagnostic id and path convention in `theme_tokens.py`.
- A Theme `outline: image` reference that the pinned Context has no
  `containerImageCatalogs` closure for is a new stable ingress diagnostic
  (`E_THEME_CONTAINER_IMAGE_UNRESOLVED` or similar; exact id decided in the
  implementation plan), raised before Layout — never a rendered blank box.
- `W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK` (#466) is unaffected: the paint
  box, not the outline choice, is what candidate search reasons about.

## Tests

- `theme_tokens.annotation_container` unit tests for the new `image` shape,
  including every additive-vs-forbidden-property rejection.
- `image_slice_geometry` unit tests mirroring `test_balloon_geometry.py`'s
  structure: degenerate zero-inset axes, asymmetric insets, a box smaller
  than the declared fixed border (must not invert tile order or produce a
  negative-size tile).
- Scene serialization round-trip for `ScenePaint.image` (identity, viewport,
  tile rects; no bytes).
- SVG adapter parity test: same tile rects render identical `<image>`
  elements regardless of whether the container is `Rect` or `Symbol` (image
  + tail together).
- `contrast_policy`/`perceptibility` regression tests proving the ground
  reported for image-backed note text is the declared `fill`, unchanged
  from a plain rectangle's ground computation (i.e., a test that literally
  asserts no branch in either module inspects `paint.image`).
- HALCYON gallery slide (acceptance 4): committed SVG/PNG/Scene evidence,
  contrast and perceptibility reports regenerated and clean.
- A Theme-without-binding regression fixture proving byte-identical output
  to the pre-#465 baseline (acceptance 5).
