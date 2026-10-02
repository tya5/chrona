# Issue #587: surface decoration, canvas texture first and glow second (work record)

Living record for [#587](https://github.com/tya5/chrona/issues/587): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `274e662c` on `main` (derived evidence `f1624ab6`). **Status:** design plan (this publication). Next: design and architecture review, then the implementation plan, then I587-1 (canvas texture) and I587-2 (glow).

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

1. **D587-1** (this PR): baseline and design plan.
2. **D587-2**: design and architecture review: decisions D1 to D10, the Spec 63, 07 and 08 amendments, the owner decision comment on the issue.
3. **D587-3**: implementation plan (slices, owned files, tests, generated evidence).
4. Code slices as planned in D587-3, then the acceptance review.
