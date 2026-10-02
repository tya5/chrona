# Issue #587: surface decoration, canvas texture first and glow second (work record)

Living record for [#587](https://github.com/tya5/chrona/issues/587): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `ded433ae` on `main`. **Status:** the design plan (section 4, PR #868) and the design and architecture review (sections 5 and 6, PR #872) are published; the implementation plan is this publication (section 7). Next: I587-1 (canvas texture), then I587-2 (glow).

## 1. Published baseline

Issue #587 has no comments before this work (body unchanged since filing; the claim is the first comment). [#454](https://github.com/tya5/chrona/issues/454) lists it as "Split per treatment; **texture and glow first**", payoff Marquee, Title Card, Sunday, Montmartre, Off-World. Depth B. Read at `274e662c` (read from code and the targets' READMEs, not from the target images):

1. **No canvas texture.** `SceneSurface.canvas_paint` is one flat or gradient fill; `v05_svg` draws it as the first rect. Title Card ("faint hexagon lattice over the canvas"), Montmartre (vignette and grain, drawn above everything) and Off-World (rain, scanlines) ask for a texture; Title Card and Off-World are the two that fit a periodic tile.
2. **The pattern machinery already exists and is the right carrier.** #496 added catalogue patterns: a normalized tile of circles, rectangles and stroked paths, completed by Layout (`pattern_placement.complete_pattern_placement`: tile, angle, density, origin, region, clip), attached to a Rect primitive by Scene (`_attach_completed_patterns`), serialized as scene v0.7 `pattern` data and drawn by `v05_svg` as an SVG `<pattern>` (resvg paints it for PNG). It is admitted on a closed set of Rect roles (`capabilities._CATALOG_PATTERN_ROLES`); `canvas` is not one of them and `background` (the canvas role) carries only flat paint, gradient and shadow. #718 merged the `chrona-target-parts` catalogue (`hexagon-lattice`, `ben-day-dots`, `hazard-stripes`, `bulb-row`, ...), so a texture needs no new bundled bytes.
3. **A catalogue pattern has an opaque substrate.** `v05_svg.catalog_pattern_body` requires `fill` (substrate), `stroke` (ink) and opacity 1. A texture drawn below the content therefore repaints the canvas colour as its substrate; one drawn above content cannot be expressed (Montmartre's grain-over-everything is outside this carrier).
4. **Typst and TikZ reject any primitive that carries a pattern** (`E_VISUAL_CAPABILITY_UNSUPPORTED`); SVG and PNG draw it; the baseline visual profile admits `paint.pattern-geometry`, so a texture paints in the default baseline profile for SVG and PNG.
5. **Contrast and perceptibility gates know grounds.** `scene/contrast_policy._ground_under` picks the latest earlier Rect that contains a primitive's sample point, else the flat canvas fill. A catalogue pattern host contributes only its `fill` there. `perceptibility._paint_findings` emits `I_SCENE_PAINT_CONTRAST` against the flat canvas. Neither knows that a texture's ink is also a ground a mark or text can lie on.
6. **No glow.** `specification 63` says the vocabulary is closed and lists "glow/blur" as not admitted. Completed paint has `LinearGradient`, `DropShadow` (finite offsets, blur 0..64, opacity, fidelity) and `StrokeFinish`. `v05_svg` draws a shadow as `<filter><feDropShadow .../></filter>` with SVG's default filter region (the element's box plus 10 %), so a blur wider than 10 % of a small element is clipped: a shadow filter cannot carry a glow around a 12 px star. Only the bundled `elevated-light` Theme and one Controller Z Theme use shadows.
7. **The #478 ladder exists.** `visual_capabilities.RICH_CAPABILITIES` holds the four rich IDs; `resolve_scene_paint` returns `PaintOmission` facts for a `decorative-optional` treatment the selected profile does not admit; Scene dedupes them into `I_VISUAL_TREATMENT_OMITTED:role=...;treatment=...;profile=...;paintable=...` (Spec 63 section 3). A new treatment joins by a capability ID, a `PaintOmission` treatment name and the fidelity property.
8. **Theme property additions are in place.** Spec 56 section 3.2 ("Theme schema additions follow the same rule"); the #492 `tickLength` precedent added one role property to `theme-v0.11` and `theme-v0.13` with no version bump.
9. **Title border, panels with gutters, as-of cone: not started.** There is no slot frame role, no Layout Profile region frame or gutter, and no gradient polygon primitive. A Path primitive carries no fill and no gradient (`_PATH_PAINT`); `Rect` is the only filled geometry besides `Symbol`. Section 4 treats each as a separate design.

Inferred (to be confirmed by the slice that touches it): that a texture Rect painted first at paint order 0 is below every other primitive (ties are broken by emission index); that the pseudo-slot precedent `review-surface` is the right way to give a canvas-wide primitive a slot; that resvg paints a `userSpaceOnUse` filter region as SVG does.

Unverified: the rendered look of any new treatment; corpus bytes after each slice (read in the verification slices); the Typst/TikZ routes for a glow (the typeset adapters ignore gradient and shadow today, so the profile gate, not the adapter, must reject a required glow).

## 2. Literal acceptance (copied from the issue)

1. Each treatment is declared, and a synthetic test covers it. Perceptibility and contrast gates treat texture and cone as ground where text overlies them.
2. Treatments beyond the baseline profile follow #478: omitted with `I_VISUAL_TREATMENT_OMITTED` naming the profile that paints them.
3. Evidence: Marquee, Title Card and Sunday surfaces through YAML.

The issue's "Need" and "Proposal" list five treatments: canvas texture, a decorated title border of repeated elements, panels with gutters, an as-of light cone, and a glow. Row 1 says "each treatment". It is met only when all five are declared and tested, or when a treatment not delivered is narrowed with a successor issue that is itself linked from the review.

## 3. Dependencies and neighbours

- #496 (catalogue patterns, closed) and #718 (packaged parts, open, another agent): the texture reuses the catalogue pattern vocabulary and the packaged `chrona-target-parts` catalogue; no preset, catalogue or part file is edited here.
- #478 (visibility ladder, closed): the glow follows it; the texture needs no omission because the baseline profile paints patterns.
- #582 (named periods), #583 (group bands and headers): other agents' files. This work does not touch Project schema, the date-range resources, group band or group header code, nor `src/chrona/resources/presets/**`.
- #588 (wobble) is a sibling treatment on the board and is not part of this issue.

## 4. Design plan

### Use cases

- **U1.** A Title Card style Theme declares a faint hexagon lattice over the canvas. The lattice paints under every mark and label, is identical on every render, and the contrast gates measure marks and state text against both the substrate and the lattice ink.
- **U2.** An Off-World style Theme declares scanlines as a texture (a tile of one thin rectangle). Rain is a different matter (section decision D4).
- **U3.** A Marquee style Theme gives its gold gate stars a glow. A Theme author declares one colour, blur and opacity; the halo is not clipped by the element's box and stays inside the slide.
- **U4.** The same Theme rendered under the baseline profile: a decorative-optional glow is omitted and reported as `I_VISUAL_TREATMENT_OMITTED` naming the SVG or PNG profile that paints it; a required glow fails before serialization with `E_VISUAL_CAPABILITY_UNSUPPORTED`.
- **U5.** A Theme without any new property renders byte for byte as before (every committed Theme).
- **U6.** An author asks for a title border, panels with gutters, or an as-of cone: each is its own successor issue with its own design (section decision D9).

### Open decisions (each is decided in the design, with the choice recorded on the issue)

- **D1. Slicing and order.** Per treatment, texture and glow first (the board). Others only after both are merged and only where they can be completed well.
- **D2. How a texture reaches the Scene.** Option A: a new `SceneSurface` field beside `canvas_paint` (clean ownership, but a Scene schema field, a version rule, and a new branch in every adapter). Option B: an ordinary Rect primitive with a catalogue pattern, owned by a Layout shape and a pseudo-slot, drawn first (no schema change; Typst and TikZ reject it already; one more role in the existing pattern allowlist).
- **D3. Texture authoring surface.** A Theme role (`canvas-texture`) with the existing `pattern`, `fill` (substrate) and `stroke` (ink) properties, or a new property on `background`. Whether the Theme chooses the paint order. Whether the substrate may differ from the canvas fill.
- **D4. Determinism, seeds, and what a texture is.** A texture is a periodic tile from a declared catalogue pattern: no random source, no hash or iteration order, no generator; the same Theme gives the same bytes. Whether a seeded generator (grain, rain) is admitted now.
- **D5. Ground rule for the gates.** How a texture counts as ground for contrast classes, for the `I_SCENE_PAINT_CONTRAST` observation and for text occlusion; whether it needs a contrast floor of its own.
- **D6. How a glow reaches the Scene.** A typed completed `Glow` paint fact, or a zero-offset `DropShadow` with a changed filter region.
- **D7. Glow authoring surface and admission.** Theme properties, the roles that may carry them, whether a shadow and a glow may share a role, the capability ID, and whether it joins the existing v0.6 profiles or a new profile.
- **D8. Adapters.** SVG and PNG paint; Typst, TikZ and PDF behave as the profile ladder says. Where a filter region is completed and by whom.
- **D9. The other three treatments.** Title border (repeated-glyph slot frame), panels with gutters (Layout Profile region frame), as-of cone (gradient polygon): which, if any, is completed in this issue, and the successor issue for each that is not.
- **D10. Committed evidence.** Row 3 asks for Marquee, Title Card and Sunday through YAML. What can be shown by texture and glow alone, where, and without editing a preset or corpus data.

### Responsibility boundaries

- Theme declares appearance (roles and properties); View selects nothing new; Layout owns completed geometry (the texture's region, tile phase and clip, the pseudo-slot, the glow's filter region if D6/D8 give it to Scene); Scene carries completed primitives and paint facts and resolves optional omission against the selected profile; adapters serialize completed values only and never read Theme, Scheme or profile.
- Core rules stay project-independent: no rule names a target, a preset or a corpus file. Theme and View YAML carry the target look.

### Data and resource model, migration

- A Theme gains an optional role (`canvas-texture`) and optional role properties for glow; both are behaviour-preserving additions, so Spec 56 section 3.2 applies (in place, no version bump) and the S0 gate `python -m tools.schema_equivalence --base-rev origin/main` runs for any schema file touched and is recorded in the PR.
- If D6 chooses a typed `Glow`, the Scene paint gains an optional field: Scene v0.7 documents get it in place and a Scene that carries one is written as v0.7; Scene v0.6 is the transitioning schema and is not edited. Confirmed or changed in the design.
- No resource migration: no committed Theme, preset or catalogue changes. Wheel size is unchanged because the texture tile comes from the existing packaged catalogue and the glow is parameters only.

### Design review questions

1. Does a texture as an ordinary Rect primitive keep ownership clean (Layout geometry, Scene paint, adapter serialization) without a Scene schema change, and is a pseudo-slot honest?
2. Does painting the texture first at a fixed paint order make "below everything" a rule rather than a Theme convention?
3. Is a periodic catalogue tile sufficient to meet "generated deterministically from declared seeds" (the tile is the declaration; there is no seed because there is nothing random)?
4. Do the contrast and perceptibility gates count both substrate and ink for every primitive that overlies a texture, including state text, marks and the generic paint-contrast observation, without a new corpus witness being forced on decorations?
5. Does a typed `Glow` with a Scene-completed filter region keep the adapter free of geometry, and does it stay inside the canvas?
6. Does adding `effect.glow` to the existing rich profiles keep every existing Theme's behaviour (no Theme declares it) and keep the baseline ladder (optional omission with `I_VISUAL_TREATMENT_OMITTED`, required failure)?
7. Is the default output unchanged by construction: no role, no property, no emission, no new bytes?

### Acceptance evidence

- Synthetic tests with no `examples/` input for each treatment delivered: Theme to Layout to Scene to SVG, a PNG raster check, the gates, the omission ladder, determinism (two renders equal), default byte identity, failure diagnostics; mutation checks of every new test.
- The S0 gate result for each schema change.
- Rendered images of every changed or new committed slide, read in full, for SVG and the PNG raster path.
- Conformance, the affected public materializers, and the exact-main three-OS run on the commit that publishes the acceptance review.

### Order of design slices

1. **D587-1** (PR #868, merged): baseline and design plan.
2. **D587-2** (PR #872): design and architecture review: decisions D1 to D10, the owner decision comment on the issue. The Spec 07, 08 and 63 amendments land with the slice that implements each rule.
3. **D587-3** (this PR): implementation plan (slices, owned files, tests, generated evidence).
4. Code slices as planned in D587-3, then the acceptance review.

## 5. Design

Decisions D1 to D10 of section 4 are taken as follows. Each is an owner-level judgement recorded on the issue with options, choice, reason and how to reverse it. The normative text goes into [Specification 07](../../specification/07-style-and-theme.md) (Theme roles and properties), [08](../../specification/08-scene-and-rendering.md) (Scene) and [63](../../specification/63-portable-visual-capabilities.md) (capabilities and profiles) with the slice that implements it, not here.

### 5.1 Slicing (D1)

I587-1 canvas texture, then I587-2 glow, each its own code PR with default output unchanged. Title border, panels with gutters and the as-of cone are not designed here beyond section 5.9; each has an independent design question (a Theme slot frame, a Layout Profile region frame, a gradient polygon) and none shares a mechanism with the first two except the omission ladder. Reverse: none needed; the order is only a plan.

### 5.2 A texture is an ordinary Rect primitive (D2)

Option A (a `SceneSurface.canvas_texture` field) is cleaner in name but adds a Scene schema field, a version rule, a branch in every adapter and a second place that knows patterns. Option B reuses what exists: a Layout shape completes one Rect over the canvas with a catalogue pattern, Scene emits it as a Rect with `pattern` data (scene v0.7 already carries it, so **no Scene schema change**), SVG and PNG paint it, and Typst and TikZ reject it exactly as they reject any pattern. Choice: B. Reverse: add the field and move the same Layout completion behind it.

- **Layout** (`layout/canvas_texture.py`, new; not a `surface_*` module, because Spec 33 section 8.3 names every `surface_*` phase module and the texture is a helper beside `pattern_placement`): `complete_canvas_texture(theme_tokens, canvas)` returns nothing when the resolved Theme has no `canvas-texture` role, and otherwise one `ShapePlacement` (`placement_id` `canvas-texture`, `semantic_id` `canvasTexture`, kind Rect, bounds = the completed canvas, `paint_order` 0, slot `canvas`) and its `PatternedPlacement` from `complete_pattern_placement` (origin is the canvas top-left, so the lattice phase is fixed by the canvas, not by content). Both Layout-completed surfaces call it, so a Theme's texture does not depend on the View kind: the table-timeline surface in `complete_surface_layout` after `completed_canvas` (its shape joins `SurfacePlacement.shapes`, its pattern `SurfacePlacement.patterns`, its slot `SurfacePlacement.slots`), and the dependency-network surface in `compose_dependency_network_layout` after its completed canvas (the placement joins `DependencyNetworkLayout.patterns`; its Scene builder adds the Rect and the `canvas` Scene slot, because that surface builds its slot list from the manifest decisions rather than from a placement). A surface with no completed canvas has no texture.
- **Slot.** The Rect needs an owner. Layout adds one pseudo-slot `canvas` (source `canvas`, bounds = canvas) next to the existing `review-surface` pseudo-slot, only when a texture is declared. The Scene slot list therefore changes only for a Theme that declares a texture.
- **Order.** The texture is the first primitive Scene emits and has paint order 0. Primitives paint by `(paint_order, emission index)`, so it is below every primitive whatever order the Theme gives a band or a mark. This makes "below everything" a rule; the Theme has no `backgroundPaintOrder` for it (the role does not admit one).
- **Scene.** `semantic_registry` gains `canvasTexture` (kind decoration, purpose `canvas-texture`, Scene and Theme role `canvas-texture`, **no contrast class**). The builder emits it first, attaches the pattern through the existing `_attach_completed_patterns`, and paint resolves as a catalogue pattern (`PaintFamily.SOLID`).

### 5.3 Authoring surface (D3)

A Theme declares the role `canvas-texture` with `pattern` (a typed pattern token of kind `catalog`), `fill` (the substrate) and `stroke` (the ink). The role is admitted for those three properties only, in the catalogue-pattern allowlist of Spec 07. Absent role means absent texture; there is no `none` spelling. A role without a catalogue pattern, with an inline pattern kind, with an `opacity` other than 1, or with any other property is `E_THEME_ROLE_REQUIRED` or `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at its exact pointer (the existing role-admission and `validate_pattern_paint` paths).

The substrate is declared, not inherited from `background.fill`: resolution "without defaults" is the rule of `resolve_scene_paint`, and a Scheme binding `canvas-texture.fill: surface` states the intent. The substrate is opaque and paints over the canvas fill (a canvas gradient under a texture is hidden; section 5.4 records the consequence for the gates and 5.9 the successor for a transparent texture). The Theme schema needs no new property: `canvas-texture` is a role name and `pattern`, `fill`, `stroke` exist, so `schema_equivalence` is expected to report no change; it is run and recorded all the same.

### 5.4 Determinism and seeds (D4)

A texture is the repetition of a declared catalogue tile from a fixed origin. Nothing is random, nothing depends on hash or iteration order, and no generator runs, so two renders of one Theme are byte-identical and there is no seed to declare. A future generator (grain, rain) must declare its seed and algorithm in the Theme and use a specified PRNG, never Python's `random` or dictionary order; that is recorded in the successor issue (5.9), not designed now. Wheel size: no bundled byte is added (the lattice is in the packaged `chrona-target-parts` catalogue).

### 5.5 Ground rule for the gates (D5)

A texture is ground, not content. Its substrate and its ink are both colours a mark or a label can lie on.

- `contrast_policy`: when the host of a classified primitive is a `canvas-texture` Rect, the ground is both the substrate and the ink. For a flat primitive the finding carries the **worse** of the two (the minimum ratio) with `groundKind` `texture-substrate` or `texture-ink`, so it still has one finding per channel; a catalogue-patterned primitive already has one finding per channel pair, and the texture adds the pairs against its ink.
- `perceptibility`: with a texture present, `I_SCENE_PAINT_CONTRAST` is measured against the worse of the substrate and the ink instead of the canvas fill (the substrate covers the canvas).
- The texture itself has no contrast floor: a faint lattice is the point, and an unclassified role forces no new corpus witness (the decoration witness requires every classified decoration role to be painted in committed evidence).
- Occlusion: the texture is never later than a text, so it cannot raise `E_SCENE_TEXT_OCCLUDED`.

### 5.6 Glow is a typed completed paint fact (D6)

Option A (a zero-offset `DropShadow` with a different filter region) needs no schema change, but an adapter would then decide that "offset zero means widen the region", and nothing in the Scene would say that this is a halo. Option B adds an optional completed `Glow(color, blur, opacity, fidelity, region)` to `ScenePaint`. Choice: B, because it makes the omission ladder, the capability ID and the filter region explicit, and because Scene already completes geometry-dependent paint (the gradient endpoints) from primitive bounds. `region` is the primitive's visible extent grown by 3 blur on every side and intersected with the canvas: the halo cannot leave the slide and is not part of the primitive's bounds, so it changes no collision, hosting or measurement. A Path's extent is the box of its points (a relation primitive's `bounds` are zero).

Scene serialization writes `paint.glow` as `{color, blur, opacity, fidelity, region}`; `schemas/scene-v0.7.schema.yaml` gains the optional definition in place and a Scene that carries a glow is written as `chrona/scene/v0.7`. Scene v0.6 is the transitioning schema and is not edited. The perceptibility and contrast readers already accept both versions. Reverse: option A, with the Scene field removed.

### 5.7 Glow authoring and admission (D7)

Theme role properties `glowColor` (a Colour Scheme binding, `<role>.glowColor`), `glowBlur` (number, 0 < blur <= 64, the shadow limit), `glowOpacity` (0..1) and `glowFidelity` (`required` or `decorative-optional`). All of colour, blur and opacity are declared together or none (`E_VISUAL_CAPABILITY_VALUE`); limits are `E_VISUAL_CAPABILITY_LIMIT`; fidelity is `E_VISUAL_CAPABILITY_FIDELITY`. The properties are admitted exactly where the shadow properties are: roles whose completed primitive is Rect, Symbol, Text or Path (the `_RECT_PAINT`, `_TEXT_PAINT` and `_PATH_PAINT` sets), and not on the canvas, on Icon-shared roles or on the shared `text` role. A role that declares both a shadow and a glow is `E_VISUAL_CAPABILITY_VALUE` at `glowBlur`: one effect per primitive, as one `filter` per element.

Capability: `effect.glow` is a new ADMITTED entry (owner Theme) in the closed ceiling, and joins `RICH_CAPABILITIES`, so all four rich profiles (`v0.6-svg`, `v0.6-png`, `v0.7-svg`, `v0.7-png`) paint it and the baseline does not. Under the baseline a `decorative-optional` glow is omitted with `I_VISUAL_TREATMENT_OMITTED:...;treatment=glow;profile=...;paintable=<first rich profile>` and a `required` glow fails before serialization with `E_VISUAL_CAPABILITY_UNSUPPORTED`. Joining the existing profile identifiers instead of minting a new one is a judgement call: no committed Theme declares a glow, so no existing result changes, and a new identifier would force every suggestion, test and render-context enumeration to name a profile that differs only by one ID. Reverse: split the ID out into a new profile identifier and move the suggestion. Spec 63 (vocabulary, profile table, omission text) and the capability prior-art matrix (generated) change with the slice.

### 5.8 Adapters (D8)

SVG draws a glow as one filter per glowing element, with identity from the completed glow (which includes its region): `filterUnits="userSpaceOnUse"` over `region`, a Gaussian blur of the element's alpha, flooded with the glow colour at its opacity, composited and merged twice under the source graphic (the double halo reads as a glow where a single feDropShadow reads as a faint shadow). PNG is the same SVG through the pinned resvg; both are rendered and read. PDF, Typst and TikZ never receive a glow: their profiles do not admit it, so the profile gate (Scene) decides, never the adapter. The existing drop-shadow filter is unchanged, byte for byte.

### 5.9 The other treatments (D9)

Not designed in this publication; each is recorded as a successor with its direction, searched first for a duplicate (none exists at `274e662c`):

- **Title border of repeated elements** (Marquee bulbs): a Theme slot-frame role on the title slot whose border is a repeated catalogue glyph along the slot edge; needs a Layout completion of the glyph run (count, spacing, corners) and a Scene emission of Symbol parts; the packaged parts exist (#718 `bulb-row`).
- **Panels with gutters** (Sunday): a Layout Profile region frame and gutter declaration (a Layout Profile schema change under Spec 56 section 3.2); frames are Rects with stroke drawn behind a region's slots.
- **As-of light cone** (Marquee): a gradient polygon from the top of the plot to its foot beneath the marks; needs a filled, gradient-capable polygon primitive (a Path carries neither fill nor gradient today) or a gradient Rect plus clip, and contrast handling as ground.
- **Texture beyond the opaque tile** (Montmartre grain above content, Off-World rain over a gradient): a transparent-substrate pattern, an overlay paint order, and seeded generators.

### 5.10 Committed evidence (D10)

Controller Z (`examples/controller-z/`) gains new slides, as #492 added `axis-ticks`, and no existing slide, preset or corpus datum is edited: a dark Theme that declares `canvas-texture` with `chrona-target-parts:hexagon-lattice` (the Title Card surface), and a Theme that gives the milestone gate a glow (the Marquee star). They are evidence against the targets, not a core criterion; the synthetic tests are the core criterion. Sunday needs panels, so acceptance row 3 is narrowed unless the panels slice is delivered.

## 6. Architecture review

- **Ownership.** Theme declares; Layout owns the texture's region, phase, clip and pseudo-slot; Scene owns the glow region and the omission ladder and emits the texture as an ordinary primitive; adapters serialize completed values and read neither Theme, Scheme nor profile. No new Layout-to-Scene back channel.
- **Layering.** `layout/canvas_texture.py` imports `pattern_placement`, `surface_quality` and `model` types only, like its neighbours; `scene` imports nothing new from Layout. `tools/check_import_direction.py` is expected to stay green.
- **Default output.** No Theme role, no property, no pseudo-slot, no emission, no filter, no schema field is written unless declared. Every committed Scene and SVG must be byte-identical after each slice; that proves "default unchanged" only, not quality.
- **Regression surface.** Texture: the role allowlist, the semantic registry, the builder's first emission, two contrast evaluators, and the slot list (only with a texture). Glow: the paint resolver, the capability ceiling and profile, the closure role admission, serialization and schema, the SVG filter. Existing `drop-shadow` behaviour is untouched.
- **Failure behaviour.** All new failures are existing codes at exact Theme pointers (`E_THEME_ROLE_*`, `E_VISUAL_CAPABILITY_*`); no new code except none is planned. A texture with no completed canvas fails closed (no texture), never a partial one.
- **Adjacent designs.** #496 (catalogue patterns) is reused unchanged; #478 (ladder) gains one treatment; #718 supplies the tile and is not edited; #582 (named periods) and #583 (group bands and headers) add Rects and bands whose paint order is above 0 and whose ground, where text lies on them, is the later band, so the texture is not their ground. Spec 56 section 3.2: Theme additions in place.
- **Risks.** (1) A texture under an opaque canvas gradient hides the gradient (recorded; successor for a transparent texture). (2) A texture on a very large canvas emits one pattern fill, not per-tile geometry, so size is constant. (3) Contrast evaluators that look up a host by "latest earlier Rect" now find the texture for primitives not on any band; the change is that they measure against substrate and ink, and a unit test pins it. (4) The double-halo glow is intentionally brighter than a drop shadow of the same parameters; the Theme owns the strength through opacity and blur.
- **Extension points.** A new texture is a new catalogue pattern; a transparent, overlay or seeded texture is a successor with its own admission; a glow on Icon needs the Icon adapter to serialize outer paint (not done).
- **Decision:** approved for implementation planning.

## 7. Implementation plan

Two code publications, each its own PR with `Refs #587`, each with default output unchanged. Generated Scene and SVG evidence of a committed slide is produced by the derived sync after the merge (CI rejects PR edits to manifest-declared evidence); locally it is regenerated into a scratch directory with `tools/regenerate_public_examples.py` to be inspected. Every committed Scene and SVG that exists before a slice must be byte-identical after it, which proves only that the default is unchanged.

### I587-1: canvas texture

- **Files.**
  - `src/chrona/presentation/layout/canvas_texture.py` (new): `complete_canvas_texture(theme_tokens, canvas)`; nothing without a `canvas-texture` role.
  - `src/chrona/presentation/layout/surface_completion.py`: call it after `completed_canvas`; append the shape, its pattern and the `canvas` pseudo-slot to the `SurfacePlacement`.
  - `src/chrona/presentation/layout/dependency_network.py`: the same call for the network surface; its pattern joins `DependencyNetworkLayout.patterns`, the Rect and slot are added by the builder.
  - `src/chrona/presentation/model/semantic_registry.py`: the `canvasTexture` binding (no contrast class).
  - `src/chrona/presentation/scene/v05_builder.py`: emit the texture Rect first on both surfaces, attach its pattern through the existing path, add the `canvas` Scene slot of the network surface.
  - `src/chrona/presentation/scene/capabilities.py`: role contract for `canvas-texture` (`fill`, `stroke`, `pattern`; consumer "Layout canvas texture and Scene Rect") and its entry in the catalogue-pattern allowlist.
  - `src/chrona/presentation/color_scheme.py`: where the resolved Theme's roles are admitted, a `canvas-texture` role without a `pattern`, or with an inline pattern, fails with `E_THEME_ROLE_REQUIRED` or `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at `/body/roles/canvas-texture/pattern`. Layout treats a resolved role that names no pattern as no texture (fail safe for a hand-built Theme), and an inline pattern as an error.
  - `src/chrona/presentation/scene/paint_analysis.py`, `contrast_policy.py`, `perceptibility.py`: the ground rule of section 5.5.
  - `docs/specification/07-style-and-theme.md` (the role and its admission), `08-scene-and-rendering.md` (the texture primitive and the `canvas` pseudo-slot).
  - Schemas: none expected (`schema_equivalence --base-rev origin/main` is run and recorded).
  - Not touched: presets, catalogues, the Controller Z or HALCYON corpus data, #582 and #583 files.
- **Tests (synthetic, no `examples/` input).**
  - `tests/unit/chrona/presentation/layout/test_canvas_texture.py`: absent role gives nothing; declared role gives one Rect over the completed canvas, paint order 0, slot `canvas`, origin at the canvas top-left, pattern equal to the catalogue entry; a non-zero canvas origin; a canvas larger than the viewport.
  - `tests/unit/chrona/presentation/scene/test_canvas_texture_scene.py`: first primitive on both surfaces, below a band of any paint order; the `canvas` slot present only with a texture; role admission rejects a texture with an inline pattern, a missing `fill` or `stroke`, an opacity other than 1, a `strokeWidth`, a gradient, a shadow, a `backgroundPaintOrder`; contrast policy measures a mark and a state text against the worse of substrate and ink (and a primitive on a later band against the band only); `I_SCENE_PAINT_CONTRAST` uses the worse ground; a texture needs no contrast floor of its own.
  - `tests/integration/test_canvas_texture_render.py`: end to end through `tests/support/synthetic_review.py` with a catalogue fixture: SVG has one `<pattern>` and one patterned Rect as the first drawn shape after the canvas; PNG (resvg) shows ink pixels at lattice positions and substrate elsewhere, and a mark pixel above it; two renders are byte-identical; a Theme without the role is byte-identical to the render before the change; Typst and TikZ reject it with `E_VISUAL_CAPABILITY_UNSUPPORTED`; both surface kinds.
- **Mutation checks.** Each new test is run against a deliberately broken implementation and must fail: emit the texture last; give it a non-zero paint order; drop the substrate; use `background.fill` as substrate; skip the network surface; add the slot without a texture; ignore the ink in the contrast ground; ignore the substrate; return the better ground; admit an inline pattern; origin at the viewport instead of the canvas. Results are listed in the PR.
- **Committed evidence.** A new Controller Z slide `surface-texture` (view, Theme, context and a manifest entry, as #492 added `axis-ticks`): a dark Theme (version `chrona/theme/v0.13`, the version that admits catalogue patterns) that declares `canvas-texture` with `chrona-target-parts:hexagon-lattice`, so the Title Card surface exists as YAML. SVG and PNG of it are read in full; the rest of the corpus is byte-identical.
- **Acceptance gates.** Focused tests, the neighbouring suites (scene, layout, closure, role admission), `conformance/run_conformance.py`, `tools/check_import_direction.py`, `tools/regenerate_public_examples.py --check`, the S0 gate result, and the PR checks including `derived-ready`.
- **Publication boundary.** One PR; merged with the merge lock; the next slice bases on the derived-sync bot commit that follows it.

### I587-2: glow

- **Files.**
  - `src/chrona/presentation/scene/model.py`: `Glow` and `ScenePaint.glow`.
  - `src/chrona/presentation/scene/paint.py`: resolve `glowColor`, `glowBlur`, `glowOpacity`, `glowFidelity`, the region from the primitive extent and the canvas, the shadow-and-glow conflict and the omission; `src/chrona/presentation/scene/v05_builder.py`: pass the canvas bounds and a Path's point extent.
  - `src/chrona/presentation/scene/capabilities.py`: the `effect.glow` entry, the properties on the Rect, Text and Path paint sets, closure role admission; `src/chrona/presentation/scene/visual_capabilities.py`: the ID in the rich capability set and in `validate_surface_visual_profile`.
  - `src/chrona/presentation/model/info_diagnostics.py`: the `glow` treatment; `src/chrona/presentation/color_scheme.py` and `src/chrona/presentation/model/closure.py`: the `glowColor` binding.
  - `src/chrona/presentation/scene/serialization.py` and `schemas/scene-v0.7.schema.yaml`: `paint.glow`, version choice; `schemas/theme-v0.11.schema.yaml` and `schemas/theme-v0.13.schema.yaml`: the role properties and the `glowColor` binding pattern, in place; the S0 gate result is recorded.
  - `src/chrona/presentation/renderers/v05_svg.py`: the glow filter; the shadow filter is untouched.
  - `docs/specification/07-style-and-theme.md`, `08-scene-and-rendering.md`, `63-portable-visual-capabilities.md` and the generated capability prior-art matrix.
- **Tests (synthetic, no `examples/` input).**
  - Unit: limits, together-or-none, fidelity, conflict with a shadow, admission on Rect, Symbol, Text and Path roles and rejection on the canvas, Icon and shared `text` roles; region equals extent plus three blur, clipped to the canvas; a Path's region from its points; omission and `I_VISUAL_TREATMENT_OMITTED` for `decorative-optional` under the baseline and `E_VISUAL_CAPABILITY_UNSUPPORTED` for `required`; the suggested profile; deduplication; scene serialization and the schema.
  - Integration: SVG filter markup and identity; PNG pixels of a halo around a mark, inside the region and absent outside it, and the glow not clipped at the element box; two renders equal; a Theme without the properties byte-identical to before; the existing shadow filter bytes unchanged; Typst, TikZ and PDF routes never receive a glow.
- **Mutation checks.** Drop the region growth; skip the canvas clip; use the shadow region; omit a `required` glow; fail a `decorative-optional` one; skip the conflict check; drop the capability from the rich set; single halo instead of double; swap colour and flood opacity. Results are listed in the PR.
- **Committed evidence.** A second Controller Z slide `surface-glow` (or the glow on the texture slide's gates, decided when it is built) whose Theme gives the milestone gate a gold glow (the Marquee star), rendered under the rich SVG profile; SVG and PNG are read in full.
- **Acceptance gates and boundary.** As I587-1.

### I587-3: acceptance

The acceptance review `docs/reviews/current/issue-587-surface-decoration-acceptance-review-<date>.md` with the `chrona:literal-acceptance/v1` marker and one row per literal criterion; any treatment not delivered is narrowed with a linked successor issue; checked by `tools/check_issue_acceptance_reviews.py`; merged; the exact-main three-OS run on the review commit located; #587 closed only when every row is met or narrowed with a successor and the full matrix and `reproduction-newest-python` are green on that commit. Successor issues (title border, panels with gutters, as-of cone, texture beyond the opaque tile) are filed before the review, each short, with direction, after a duplicate search.
