# Implementation Plan — Image-Backed Annotation Container (#465)

**Public design base:** the commit that publishes the [architecture
review](../../reviews/current/issue-465-image-annotation-container-architecture-review-2026-09-27.md).
**Authority:** [design](../../design/issue-465-image-annotation-container-design-2026-09-27.md),
[Specification 65 draft](../../specification/65-container-image-assets.md),
[Issue #465](https://github.com/tya5/chrona/issues/465).

## Literal acceptance ledger

1. A Theme can bind an image to the annotation container, with stretch
   insets and a content inset. A View cannot.
2. Layout measures and wraps note text inside the content inset, and the
   image is stretched to the resulting box.
3. Contrast and perceptibility checks treat the image's content area as
   the ground for the note text.
4. One committed slide renders HALCYON-1 `02-programme-board` with
   image-backed notes, and its SVG and PNG evidence is reproducible.
5. A Theme without the binding renders exactly as today.

## Coordination

The other dev session owns #466/#467. #465 does not touch their placement
search, lane packing, or connector-topology code; it only adds a Theme
outline and a Scene paint mode the existing `Rect`/`Symbol` annotation-box
projection already supports the shape for. Before each push, fetch
`origin/main`, check ahead/behind, and stop on a conflict in
`layout/surface_composer.py`, `theme_tokens.py`, or any HALCYON `02`
Theme/View document #466/#467 are actively patching (per the C3
sequencing correction). I465's own evidence slide (I465-5) targets a *new*
document, not `02-programme-board`, specifically to avoid this contention.

**One decision needed before I465-1 starts:** the architecture review's
ambiguity 1 (a new sibling resource kind for container art, versus
extending `chrona/icon-catalog/v0.3`). This plan is written for the
sibling-resource-kind reading; if the lead prefers the alternative, only
I465-1's target files change (see that slice's note), not I465-2 through
I465-6.

## I465-1: container-image asset family and Context closure

**Owners/files:**
- New resource kind module (mirrors `src/chrona/presentation/icons.py`'s
  identity/closure shape but without icon accessibility fields), e.g.
  `src/chrona/presentation/container_images.py`.
- `schemas/container-image-catalog-v0.1.schema.yaml` (new).
- `schemas/render-context-v0.17.schema.yaml` (new, additive
  `inputs.containerImageCatalogs`); `contracts/resources.py` schema
  registration table gains the two new `(kind, version)` entries.
- A small deterministic script under `tools/` (e.g.
  `tools/generate_container_image_placeholder.py`) that emits one
  repository-owned nine-slice PNG (bordered panel, no photographic
  content) and its normalized catalog document — this is the one
  committed placeholder asset for I465-5, not a general importer.
- *If the lead instead chooses the icon-catalog-extension reading:* skip
  the new schema/resource-kind files above and instead extend
  `chrona/icon-catalog/v0.3`'s PNG-entry path and its Context input; the
  remaining slices are unaffected.

**Focused tests:**
- catalog document parses, identity is a stable SHA-256 of the PNG bytes;
- duplicate/unknown/ambiguous `set:name` reference rejections (mirroring
  Specification 64 §2's existing test shapes);
- Context closure resolves a pinned `containerImageCatalogs` reference and
  rejects an unpinned one before Layout;
- the placeholder-generation script is itself deterministic (byte-identical
  output across two runs) — checked as an ordinary unit test, not only by
  eye.

**Public evidence:** none yet (no Theme/View consumes this input until
I465-2).

**Gate:** focused tests only; this slice adds no Layout/Scene behavior.

## I465-2: Theme `annotationContainer.image`

**Owners/files:**
- `schemas/theme-v0.11.schema.yaml`: additive `outline: image` branch on
  the existing `annotationContainer` value shape (`image`, `sliceInsetsEm`,
  `contentInsetEm`; `cornerRadius` forced to `0`).
- `src/chrona/presentation/model/theme_tokens.py`:
  `ThemeTokenView.annotation_container` gains the third return shape;
  resolves the `image` reference against the pinned
  `containerImageCatalogs` closure (I465-1), raising a new stable
  diagnostic (exact id decided here, e.g.
  `E_THEME_CONTAINER_IMAGE_UNRESOLVED`) when the closure cannot supply it.
- `docs/specification/07-style-and-theme.md`: already updated in the
  design commit; revisit only if the schema shape changes during
  implementation.

**Focused tests:**
- every existing `annotation_container` test still passes unchanged
  (`rectangle`/`balloon` branches byte-identical);
- new `image` branch: valid binding round-trips; each of `image` /
  `sliceInsetsEm` / `contentInsetEm` missing or malformed raises
  `E_THEME_TOKEN_TYPE` at the documented path; a non-zero `cornerRadius`
  with `outline: image` raises; a reference outside the Context's pinned
  closure raises the new ingress diagnostic.

**Public evidence:** none yet (no Layout/Scene caller reads the new branch
until I465-3/4).

**Gate:** focused tests (`tests/unit/chrona/presentation/model`).

## I465-3: Layout content box, nine-slice geometry, collision

**Owners/files:**
- `src/chrona/presentation/layout/image_slice_geometry.py` (new, parallel
  to `balloon_geometry.py`): `image_slice_geometry(paint_box, *,
  slice_insets, viewport) -> tuple[ImageTile, ...]`, pure geometry, no
  Theme/catalog knowledge.
- `src/chrona/presentation/layout/surface_composer.py`: the annotation-box
  construction (`2264-2398`) gains a branch reading the container's third
  outline; when `image`, it (a) measures text into the content box, (b)
  derives the paint box (content box expanded by `contentInsetEm`), and
  (c) uses the paint box — not the content box — for
  `project_annotation_box`/`nearest_free_box`/obstacle registration,
  exactly where today's box is used. The `rectangle`/`balloon` branches
  are otherwise untouched; when a role has no `contentInsetEm` (i.e., not
  `outline: image`), content box and paint box stay identical, matching
  today's behavior exactly.

**Focused tests:**
- `image_slice_geometry` unit tests mirroring `test_balloon_geometry.py`:
  symmetric insets, asymmetric insets, a zero inset on one axis
  (three-slice degenerate case), a paint box smaller than the declared
  fixed border (must not invert tile order or emit a negative-size tile —
  the architecture review's named risk);
- an annotation with `outline: image` and no `contentInsetEm` fails Theme
  validation (I465-2), so this slice does not need to guard against it
  again, only assert the content/paint box split for a valid binding;
- a `rectangle`/`balloon` regression fixture proving `content box == paint
  box` and identical obstacle registration to the pre-#465 baseline
  (acceptance 5, at the Layout layer).

**Public evidence:** none yet (Scene projection is I465-4).

**Gate:** focused tests (`tests/unit/chrona/presentation/layout`).

## I465-4: Scene `ScenePaint.image` and adapter parity

**Owners/files:**
- `src/chrona/presentation/scene/model.py`: `ImageFill`/`ImageTile`
  dataclasses; `ScenePaint.image: ImageFill | None = None`.
- `src/chrona/presentation/scene/v05_builder.py`: the annotation-box
  `Rect`/`Symbol` branch (`580-589`) attaches `paint.image` when the
  resolved container outline is `image`, alongside the existing
  `paint.fill` from the role's colour binding — no new primitive `kind`.
- `src/chrona/presentation/scene/serialization.py`: `_paint` gains an
  `image` key (`assetIdentity`, `viewport`, tile source/destination rects;
  no raw bytes), parallel to the existing `gradient` key.
- `src/chrona/presentation/renderers/v05_svg.py`: one `<image>` element per
  resolved tile, reusing the existing `b64encode(icon_raster)` pattern
  (`182-184`) generalized to any primitive's `paint.image`, with the
  tile's source rect as a cropping viewBox/`preserveAspectRatio="none"`
  and destination rect as absolute geometry.
- PNG: no new code — confirm resvg continues to derive PNG from the
  changed SVG unchanged (existing pipeline).

**Focused tests:**
- Scene serialization round-trip for `ScenePaint.image` (identity,
  viewport, tile rects present; no bytes in the JSON — assert this
  explicitly, mirroring how `icon.assetIdentity` is asset-only today);
- SVG adapter: N tiles produce N `<image>` elements with the expected
  viewBox/x/y/width/height, for both a `Rect` container (no tail) and a
  `Symbol` container (image + balloon tail together);
- **contrast/perceptibility non-regression test**: assert neither
  `contrast_policy.py` nor `perceptibility.py` branches on `paint.image`
  (e.g., a fixture Scene with `paint.image` set but a mismatched `fill`
  proves the reported ground is exactly `fill`, not something derived
  from the image) — this is the direct evidence for acceptance bullet 3
  and the architecture review's "zero lines changed" claim.

**Public evidence:** none yet (I465-5 is the first public consumer).

**Gate:** focused tests (`tests/unit/chrona/presentation/scene`,
`tests/unit/chrona/presentation/renderers` or equivalent).

## I465-5: HALCYON gallery evidence slide

**Owners/files:**
- A new example context, not an edit to `02-programme-board`, e.g.
  `examples/halcyon-1/gallery/02-programme-board-image-notes/` (exact
  path confirmed against repository convention for gallery variants
  before creating it).
- A new HALCYON Theme document (or a new role added to an existing HALCYON
  gallery Theme, not the shared `02` Theme #466/#467 are patching) binding
  `outline: image` to the annotation-box role, using the I465-1
  placeholder asset, with `fill` set to that asset's actual content-area
  colour.
- `tools/regenerate_public_examples.py` renders the new context.

**Sequencing check (must happen immediately before this slice, not
assumed from the design/review):** re-read
`docs/planning/active/issue-466-c3-sequencing-correction-2026-09-27.md`'s
current state and `02-programme-board`'s HEAD Theme/View for whether
#466 C3/C4 and #467 L3 have landed. If they have, build the gallery
variant from the post-lanes `02` geometry. If not, build from current `02`
geometry and record in the slice review that the gallery variant will
need re-regeneration once lanes land (matching the C3 correction's own
disclosed limitation), per the design plan's recommendation to wait if
feasible.

**Focused tests:** CLI render of the new context succeeds with no
`W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK` regressions versus `02` itself;
before/after PNG crop inspection of the three notes.

**Public evidence:** `tools.regenerate_public_examples --write` then
`--check`; `tools/diagnostic_inventory.py`, `tools/presentation_contrast.py`,
`tools/presentation_font_identity.py`, `tools/presentation_coverage.py`
(without `--check`), then `conformance/run_conformance.py`. Expected
change: exactly one new slide's SVG/PNG/Scene JSON, plus the four
diagnostics reports gaining that slide's rows. No other committed slide's
bytes should change; attribute any that do.

**Gate:** as I465-4, plus conformance.

## I465-6: issue acceptance and corpus-count updates

**Owners/files:**
- `tests/acceptance/output/test_public_geometry_regressions.py`: bump the
  hard-coded public-slide count (and any axis-label/primitive count keyed
  to "every public slide") by exactly the new gallery slide's own
  contribution; explain the delta in the slice review, distinguishing it
  from any concurrent #466/#467 count change.
- A Theme-without-binding regression fixture proving byte-identical output
  to the pre-#465 baseline (acceptance 5) — likely already covered by
  I465-2/3's own regression tests, but restated here as the literal
  acceptance evidence.
- `docs/reviews/current/issue-465-image-annotation-container-acceptance-review-2026-09-27.md`
  (or dated at whatever date the slice actually lands): one row per
  literal criterion above, each `met`/`deferred`/`not met` with direct
  evidence, `CI: pending` for the lead to fill in.

**Gate:** focused tests, `conformance/run_conformance.py`,
`tools.regenerate_public_examples --check`, full CI on push (three-OS
pytest/conformance per repository practice).

If any slice exposes a contradiction — the fixed tail/nine-slice contract
cannot express a target's actual artwork, or `tvac-note`-style density
makes the evidence slide's plot ungeometrizable even after #467 L3 — pause,
publish a design correction and review, and amend this plan before
resuming code, per AGENTS.md.
