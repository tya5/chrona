# Design Plan — Image-Backed Annotation Container (#465)

**Base:** `adaf5afc` (main), which contains #466 C2 (`5b96ee50`): Theme
v0.11's `annotationContainer` token (`outline: rectangle|balloon`,
`cornerRadius`, `tailBaseEm`), `layout/balloon_geometry.py`, and Scene
projection of a balloon as a filled `Symbol` primitive.

## Published baseline, inference, and unverified facts

Published, verified in this worktree:

- `examples/halcyon-1/themes/briefing.yaml` paints the annotation box with
  `annotation.fill`/`annotation.stroke` only; `annotation-text.fill` paints
  the note text. (Issue body, and `src/chrona/presentation/model/theme_tokens.py`.)
- Theme v0.11 already carries an `annotationContainer` token
  (`ThemeTokenView.annotation_container`, `theme_tokens.py:255-275`) with two
  finite outlines: `rectangle` (today's plain box, unchanged bytes) and
  `balloon` (a Layout-owned closed Path — box outline plus an integrated
  triangular tail — `layout/balloon_geometry.py`). `surface_composer.py:2384-2397`
  chooses `Balloon` only when a `tail_tip` exists; otherwise it emits the
  existing plain `Rect`. `scene/v05_builder.py:580-589` projects a `Balloon`
  shape to a Scene `Symbol` primitive (`symbol=SymbolGeometry(path)`); a
  plain box stays a `Rect` primitive. Both keep the `annotation-box` semantic
  role, so today's `annotation.fill`/`annotation.stroke` colour bindings paint
  either shape unchanged.
- Icon catalogs (specification 64, `chrona/icon-catalog/v0.3`) are
  **monochrome vector or purpose-built PNG entries used as a visual companion
  beside text or over one mark**; a View names the occurrence (`visuals`,
  `chrona/view/v0.12`+). Theme never names an icon. Spec 64 §1 explicitly
  excludes "arbitrary images/artwork" from this contract, and §3 ends: "A
  future multicolour logo or image belongs to a separately designed asset
  family." The Scene `Icon` primitive requires `icon_kind in {vector,
  raster}`, `icon_viewport`, and (for accessibility) `icon_alternative` /
  `icon_decorative` — semantics built for a meaningful-or-decorative
  companion, not for structural chrome a View can never select.
- `ScenePrimitive.paint` (`scene/model.py:15-25`, `ScenePaint`) already
  supports a non-flat fill alternative to `fill`: `gradient: LinearGradient
  | None`, fully inlined as hex stops in the serialized Scene JSON. Contrast
  ground resolution (`scene/contrast_policy.py:_ground_under`) already
  handles this today via `sample_linear_gradient`, and treats any prior
  `Rect`/`Symbol` primitive with an opaque flat or gradient fill as a valid
  ground. `_paint_findings` (`scene/perceptibility.py`) evaluates contrast for
  *every* primitive with a hex `fill`, regardless of `kind`.
  Committed Scene JSON records **identity only** for a raster asset
  (`icon.assetIdentity`, `icon.viewport`), never raw bytes — the SVG renderer
  (`renderers/v05_svg.py:182-184`) embeds `icon_raster` bytes (an in-memory
  Python field, not part of the serialized document) as a base64 `<image>`
  data URI. `tools/presentation_contrast.py` and
  `tools/check_scene_perceptibility.py` read only the committed Scene JSON, so
  neither can decode pixel data from a raster asset today; any contrast/
  perceptibility "ground" they compute must be a value already present in
  that JSON.
- `chrona/render-context/v0.16` (`schemas/render-context-v0.16.schema.yaml`)
  closes `inputs.iconCatalogs`; it has been bumped five times since v0.11 for
  additive input changes, so a further additive Context bump is ordinary
  practice here (unlike View's contended version).
- `docs/planning/active/issue-466-c3-sequencing-correction-2026-09-27.md`
  (base `812d5c77`) re-sequences #466 C3/C4's HALCYON `02-programme-board`
  plot-note evidence to run **after** #467 L3 moves `02` to
  `rows.mode: lanes`; `02`'s plot geometry is therefore about to change twice
  more before #465 could safely add a fourth concern to it.
- Target research (`docs/research/presentation/{yuya,tenthframe,marquee,
  offworld}-target-2026-09-26/README.md`): four approved targets each draw a
  note over a stretchable framed image (hanging scroll, photo-booth frame,
  newspaper clipping, bracketed printout); Yuya's README states the shared
  gap explicitly ("one gap, not a per-theme effect") and names exactly the
  three needs the issue repeats: bound image, nine-slice/content-box stretch,
  content inset, contrast against the image. Tenth Frame additionally wants
  *one* container shared across several annotations (a strip); that is out of
  scope here (same boundary as #453's rail/row alignment) and is named, not
  silently absorbed.

Inferred, not directly read: the exact colour the product owner will accept
for a committed placeholder asset. Unverified: whether the
lead/owner wants a generalized third-party image-import command in this
slice (see open decision below) or a minimal hand-authored asset for now.

## Literal issue acceptance ledger

1. A Theme can bind an image to the annotation container, with stretch
   insets and a content inset. A View cannot.
2. Layout measures and wraps note text inside the content inset, and the
   image is stretched to the resulting box.
3. Contrast and perceptibility checks treat the image's content area as the
   ground for the note text.
4. One committed slide renders HALCYON-1 `02-programme-board` with
   image-backed notes, and its SVG and PNG evidence is reproducible.
5. A Theme without the binding renders exactly as today.

## Use cases and decisions to close

- **U1 (Theme-bound image container):** a Theme role's `annotationContainer`
  token grows a third `outline: image` alternative alongside `rectangle` and
  `balloon`, carrying an asset reference, nine-slice stretch insets (em), and
  a content inset (em). No View field is added or consulted; a View
  authoring an annotation with `connector.kind: tail` today already requires
  a balloon-capable role (#466) — an image outline is an independent choice
  Theme makes for the same box, connector kind aside.
- **U2 (Layout content box and stretch):** `project_annotation_box` already
  returns the box that fits the measured text; today that box *is* the paint
  box. With a content inset declared, the box Layout hands to text placement
  must be measured so that `contentBox = textBox` and `paintBox = contentBox
  expanded by the content inset on every side` (analogous to today's implicit
  zero inset). The nine-slice stretch geometry is then computed from
  `paintBox` and the declared stretch insets: fixed corner/edge tiles keep
  their declared size, the middle tile(s) absorb the rest. This is pure
  Layout geometry, parallel to `balloon_outline`.
- **U3 (Scene projection, adapter parity):** the completed nine-slice tiling
  (each tile's destination rect plus its source rect in the asset's own
  pixel space) is a Layout/Scene fact, not an adapter one — SVG and PNG stay
  dumb serializers, matching #466's "adapters do not invent a tail" rule and
  spec 64 §6 ("adapter... does not decide"). Two representations were
  weighed:
  - (a) a dedicated new primitive kind (`Image` or `ContainerImage`) with its
    own tile list, requiring `contrast_policy.py` and `perceptibility.py` to
    learn a new ground-eligible `kind`; or
  - (b) keep the container a `Rect` (plain) or `Symbol` (balloon) primitive
    exactly as today, and add an optional `image` fill mode to the existing
    `ScenePaint` (parallel to the existing `gradient` fill mode), carrying
    the asset identity and the completed tile list, while `paint.fill`
    keeps carrying the Theme-declared *representative ground colour* used by
    every existing contrast/perceptibility computation unchanged.
  (b) is chosen: it needs no change to `contrast_policy.py` or
  `perceptibility.py`'s ground-eligibility rules (`kind in {Rect, Symbol}`
  already matches both today's outlines), reuses `ScenePaint` exactly the
  way `gradient` already extends `fill`, and keeps "one container mechanism"
  literally — an image-backed box is still a `Rect`/`Symbol` primitive with
  a `paint`, just as a balloon is still one closed outline with a `paint`.
- **U4 (declared ground colour, not decoded pixels):** because committed
  Scene JSON never carries raster bytes (see baseline above), the contrast
  ground for image content cannot be computed by decoding the PNG at check
  time without changing that architecture. The Theme author instead sets the
  role's existing `annotation-box.fill` colour binding to the artwork's own
  content-area tone (Yuya's hinoki `#EFE3C8`, for instance); that colour
  becomes `paint.fill` on the Scene primitive exactly as it does today for a
  plain rectangle, and every existing ground/contrast computation treats it
  as the note's ground with no code change. A drift check (does the declared
  colour actually match the shipped artwork's content-area pixels) is named
  as an open decision below, not built into this slice.
- **U5 (asset family and store):** the image itself is **not** an icon-catalog
  entry. Two options were weighed against the brief's instruction to reuse
  "the icon catalogue... and its asset closure / content identities":
  - (a) store the artwork as a `chrona/icon-catalog/v0.3` PNG entry and let
    Theme reference it by the same `set:name` grammar View visuals use; or
  - (b) a new, sibling resource kind (a "container image catalog") that
    reuses the *identity and closure engineering* of spec 64 (SHA-256
    content identity, atomic all-or-nothing import, immutable revision,
    Context-pinned catalog set, materialization-time verification) without
    being an icon catalog.
  (a) is rejected: it would let a View accidentally select structural chrome
  through the ordinary `visuals` grammar (spec 64's icon accessibility
  contract — alternative text, decorative/meaningful classification — does
  not fit a container backdrop), and it would blur spec 64's own boundary
  ("does not own... arbitrary images/artwork"). (b) is proposed as the
  design's answer; see the open decision below asking the lead/owner to
  confirm this reading of "the store to reuse" (reuse the *pattern*, not the
  *resource kind*) before implementation.
- **U6 (evidence slide):** #466 C3/C4 and #467 L3 are about to change
  `02-programme-board`'s plot geometry twice more, and #465 must not step on
  that in-flight work (per boundaries) or duplicate its churn. #465 proposes
  a **new** committed slide/context derived from `02` (a gallery variant,
  e.g. `examples/halcyon-1/gallery/02-programme-board-image-notes/`) rather
  than editing `02-programme-board` itself. See "Evidence and corpus impact"
  below.

## Responsibility and architecture review questions

- Does defining a second, sibling asset-catalog kind (U5b) for one new
  Context input actually honour "the store to reuse," or does the lead
  intend the icon catalogue's PNG-entry mechanism itself to be widened (U5a)
  even though spec 64 disclaims arbitrary images? This is the one question
  this plan cannot close alone — flagged for the architecture review and,
  if needed, the issue owner.
- Confirm the chosen `ScenePaint.image` fill-mode keeps `contrast_policy.py`
  and `perceptibility.py` byte-for-byte unchanged, by tracing every call site
  that pattern-matches on `paint.fill`/`paint.gradient`.
- Confirm Layout's existing `project_annotation_box`/`nearest_free_box`
  collision math needs no change beyond using the *paint* box (content box
  + content inset), not the *content* box, as the obstacle/box the search
  commits — i.e., the inset is added before collision, not after.
- Confirm no View schema change is required (acceptance bullet 1 says a View
  cannot bind the image); if implementation later finds a View field is
  unavoidable, stop and ask before touching View (v0.26/v0.27 contended).

## Ordered design slices and acceptance evidence

1. **D1 — asset family and Context closure.** New resource kind for
   container-image catalogs (identity, closure, materialization), plus an
   additive `chrona/render-context/v0.17` input. No Theme/Layout/Scene
   change yet. Evidence: schema, a hand-authored placeholder asset (own
   artwork, not third-party; see risk below), closure round-trip test.
2. **D2 — Theme token `outline: image`.** Additive Theme v0.11 schema
   change: `annotationContainer.image` variant (asset ref, stretch insets,
   content inset). `theme_tokens.annotation_container` returns the new
   shape; Themes without the binding are provably unaffected (acceptance 5).
3. **D3 — Layout content box, stretch geometry, and collision.** Content
   inset changes the paint box Layout commits to the obstacle index; nine-
   slice tile geometry computed from the paint box and declared stretch
   insets, parallel to `balloon_outline`.
4. **D4 — Scene `ScenePaint.image` and adapter parity.** SVG embeds each
   tile identically to today's raster icon embedding (base64 `<image>`, one
   per tile, each with its own source/destination rect); PNG stays derived
   from SVG via resvg.
5. **D5 — HALCYON gallery evidence slide** (acceptance 4), after confirming
   #466 C3/C4 and #467 L3 land first (see coordination below) or, if not,
   built from `02`'s *current* plot geometry with an explicit note in the
   review that the gallery variant will be re-measured once those land —
   matching the C3 sequencing correction's own precedent.
6. **D6 — contrast/perceptibility/conformance evidence** for the new slide
   and for a Theme-without-binding regression fixture (acceptance 3, 5).

## Coordination and evidence/corpus impact

- The proposed evidence slide is a **new** gallery slide/context, not an
  edit to `02-programme-board`. It adds one committed SVG+PNG pair and one
  committed Scene JSON to `examples/halcyon-1/gallery/` (or an equivalent
  new example root — exact path decided in the design). This means:
  - `tools/presentation_contrast.py`/`tools/check_scene_perceptibility.py`
    corpus counts (slide count, primitive counts) grow by exactly one slide
    plus its own primitives; the five-decoration witness set gains a
    candidate scene but the witness roles are unrelated to
    `annotation-box`, so no witness-set membership change is expected.
  - `tests/acceptance/output/test_public_geometry_regressions.py` hard-coded
    corpus counts (public slide count, and any axis-label/primitive count
    keyed to "every public slide") need a deliberate, explained bump.
  - `tools/regenerate_public_examples.py` gains one more context to render;
    `--check` must be clean after `--write`.
- Because #466 C3/C4 (row 3, `tvac-note`) and #467 L3 (`rows.mode: lanes`)
  are still in flight against `02`, this plan does not depend on their
  outcome for D1–D4; only D5 (the evidence slide) needs a decision: build
  now from current `02` geometry (fastest, but the gallery variant's plot
  will visibly change again once lanes land) or wait for #467 L3 to commit
  first (avoids a second regeneration, costs a dependency). Recommendation:
  wait for #467 L3, mirroring the #466 C3 sequencing correction's own
  reasoning; flagged as a decision for the lead.

## Risks

- **Asset provenance.** A hand-drawn "hanging scroll" / "photo-booth frame"
  image close to the approved targets would need real artwork and a real
  licence; #465's evidence only needs *an* image-backed container to exist,
  not the final Yuya artwork. The design plan proposes a minimal,
  repository-owned, geometrically simple placeholder (a bordered nine-slice
  panel, generated deterministically by a small script, no photographic or
  third-party content) so the acceptance is met without a licensing
  decision the lead/owner must make about the actual target artwork. Later
  replacement with real target art is a follow-up, named here, not silently
  built now.
- **Declared-vs-actual ground colour drift.** Nothing stops a Theme author
  from declaring a `fill` that does not match the shipped artwork's content
  area. A verification tool (checking the declared colour against the
  asset's actual content-region pixels within a tolerance, at catalog-import
  time) is a natural follow-up but is not in this slice's literal acceptance;
  named as an open decision, not built now.
- **Tenth Frame's shared strip** (one container across several annotations)
  and **Marquee's rotation** are explicitly out of scope (see U6/target
  research); naming them here so they are not silently narrowed into this
  issue's acceptance.

## Next documents

- `docs/design/issue-465-image-annotation-container-design-2026-09-27.md`
  (with a Specification 65 draft for the new asset family, and a
  `docs/decisions/` ADR if the closure/versioning choice is judged
  normative).
- `docs/reviews/current/issue-465-image-annotation-container-architecture-review-2026-09-27.md`.
- `docs/planning/active/issue-465-image-annotation-container-implementation-plan-2026-09-27.md`.
