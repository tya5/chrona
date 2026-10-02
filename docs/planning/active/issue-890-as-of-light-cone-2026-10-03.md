# Issue #890: the as-of light cone (work record)

Living record for [#890](https://github.com/tya5/chrona/issues/890) (P4-B, split from #587): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `24f686f1` on `main`. **Status:** design plan, design, architecture review and implementation plan are published together by this record; no product code yet. Slices: I890-1 cone (Theme role, Layout completion, Scene gradient with stop opacity, contrast ground, SVG) with the Controller Z evidence slide, then the acceptance review. The direction was recorded in section 5.9 of the archived [#587 record](../../archive/planning/issue-587-surface-decoration-2026-10-02.md).

## 1. Published baseline

Issue #890 had no comment before the claim (body unchanged since filing, read 2026-10-03). It is a successor of #587 (texture and glow are done there). The target is Marquee ([README](../../research/presentation/marquee-target-2026-09-26/README.md): "Spotlight, As-of: dashed line, a light cone widening to the floor, chip label"). Read on `24f686f1` from code and specifications, not from images:

1. **There is a closed polygon primitive already.** A `Symbol` carries `SymbolGeometry(outline)` (move, line, quadratic commands); SVG draws it as one `<path>` with fill, stroke, opacity and gradient exactly as it draws a Rect; the chamfered axis cell (#491) is a Symbol emitted from a Layout `ShapePlacement` with `path_commands`. The issue's premise ("a Path primitive carries neither fill nor gradient") is true of `Path`, but `Symbol` is the filled-polygon primitive and needs no new kind. The baseline profile admits `geometry.symbol-outline`.
2. **Completed paint has a linear gradient.** `LinearGradient(start, end, stops, fidelity)` with exactly two opaque stops (hex colours); `paint.linear-gradient` is in the four rich profiles and not in the baseline; `resolve_scene_paint` completes the endpoints from the primitive's bounds and an angle, omits a `decorative-optional` gradient under a profile that cannot paint it (`PaintOmission`, deduplicated into `I_VISUAL_TREATMENT_OMITTED`), and fails a `required` one with `E_VISUAL_CAPABILITY_UNSUPPORTED` before serialization. **A stop cannot be transparent:** stop colours are `#rrggbb`, SVG gets no `stop-opacity`, and `paint.opacity` is one value for the whole primitive. "Ink to transparent" is therefore not expressible today.
3. **The as-of marker is a Layout `ShapePlacement`.** `surface_composer` places `as-of` (kind Path, two points at the as-of x from the plot top to the plot bottom, paint order `MARK_PAINT_ORDER_BASE` = 100) only when the as-of date falls inside the window; the label and its chip are separate. The plot is the timeline slot down to the bottom of the last row, never past the slot (`plot_rect`, #880): every overlay that runs the height of the plot ends there. A band is placed at paint order 10 (`BACKGROUND_PAINT_ORDER`), axis rules at 11 and 12, marks from 100, hosted text 200, foreground text 300, annotations 400. Bands do not enter the obstacle inventory.
4. **The contrast gate reads grounds as opaque Rect or Symbol fills.** `contrast_policy._ground_under` takes the topmost earlier covering Rect or Symbol with a `fill` (bounding box, not outline), refuses a translucent host (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`), samples an opaque gradient, and adds the ink of a canvas texture or a catalogue pattern host (#587, #884). A cone emitted as an ordinary Symbol would therefore be read as an opaque gradient host over its whole bounding box: it would (wrongly) become the ground of every band and mark inside the box, at full ink strength at the apex. The cone needs its own rule.
5. **#950 and #884 are merged** (note ink is judged on the note box; group header text is a `ground-text` class; patterned grounds count their ink). The decoration witness requires every *classified* decoration role to be painted in committed evidence; an unclassified decoration (`canvasTexture`, the chips) forces no witness.
6. **Unclassified free text is not gated at all today.** Member labels outside a bar, the as-of label and the axis labels keep the shared role `text`, which has no contrast class by design. Only classified text (state text, `ground-text`) and marks are gated, so "labels on the cone are gated as on ground" can only mean the classified ones.
7. **Theme schema additions** follow Spec 56 section 3.2 (the #587 glow added role properties to `theme-v0.11` and `theme-v0.13`, the two versions `resolve_theme` accepts, with expected-delta entries for the S0 gate). Scene v0.7 gained optional `paint.glow` the same way; a Scene that carries it is written as v0.7.
8. **Typst, TikZ and PDF** have no rich profile; under the baseline a `decorative-optional` treatment is omitted by Scene and a `required` one fails before serialization.

Inferred (to be confirmed by the slice that touches it): that no committed Scene holds a Symbol with the role name chosen here; that resvg paints `stop-opacity` on a `userSpaceOnUse` gradient as SVG does; that a plain Symbol with a fill and a gradient needs no new entry in the closed Layout emission inventory.

Unverified: the rendered look of any cone; corpus bytes after the slice (read in the verification step); the PNG rasterisation of the fade.

## 2. Literal acceptance (copied from the issue)

1. The cone is declared and completed by Layout, with synthetic tests: geometry from the as-of position, below the marks, gradient endpoints, default output unchanged without the declaration.
2. Marks and labels on the cone are gated as on ground (worst of the gradient stops it spans); the gradient follows the #478 ladder.
3. Evidence: the Marquee as-of marker through YAML, rendered through SVG and PNG and read.

Assignment constraints: defaults leave output unchanged; spread and extent are Theme tokens; the cone is clipped to the plot, ends at the last row (#880) and is ordered under marks and text; a typed omission or diagnostic when the baseline profile cannot paint a gradient; a Marquee style evidence slide through YAML only; synthetic tests read no `examples/` input; no corpus datum is edited to pass a criterion.

## 3. Dependencies and neighbours

- #587 (closed; texture, glow, the omission ladder), #478 (ladder), #880 (the plot), #884 and #950 (grounds), #428 (label chips) are reused unchanged; #718 (catalogue) is not touched.
- Other agents work on #585 (vertical writing), #893 (calendar shading), #889 (region frames and panels), #882 (group tab). This work edits none of their files: the composer edit is one call beside the existing `as-of` block, and no group band, calendar, panel or text-direction module is touched. Shared files (`scene-v0.7.schema.yaml`, `theme-v0.11/0.13.schema.yaml`, `expected-deltas-v0.1.yaml`, `capabilities.py`) are rebased carefully before every push.

## 4. Design plan

### Use cases

- **U1.** A Marquee style Theme declares a warm cone from the as-of marker: bright where it leaves the top of the plot, fading to nothing toward the foot, widening as it falls, under the bars and gates, over the row bands, ending at the last row.
- **U2.** The same Theme under the baseline profile: a `decorative-optional` cone is omitted completely (never a flat ink polygon) and reported as `I_VISUAL_TREATMENT_OMITTED`; a `required` one fails before serialization with `E_VISUAL_CAPABILITY_UNSUPPORTED`.
- **U3.** A bar, gate or state label inside the cone is judged on the ground it truly lies on (band or canvas with the cone's ink composited at the strength the gradient has where it lies); a mark that straddles the edge is judged on both.
- **U4.** A Theme without the role renders byte for byte as before (every committed Theme).
- **U5.** The cone follows the as-of marker: no as-of date in the window, no cone.

### Open decisions (each is decided in section 5 and recorded on the issue)

- **D1** the primitive: a filled polygon (Symbol) or a gradient Rect plus a clip.
- **D2** how "ink to transparent" reaches the Scene.
- **D3** the authoring surface: Theme role, properties and defaults.
- **D4** the geometry: apex, spread, extent, clipping and the unit of spread.
- **D5** the paint order, and whether the cone is an obstacle.
- **D6** the ground rule for the gates, including the worst-of-stops rule and where the cone is not a ground.
- **D7** the omission ladder and capability.
- **D8** adapters and Scene version.
- **D9** the evidence slide.

### Responsibility boundaries

Theme declares appearance (role `as-of-cone`: ink, strength, spread, extent, fidelity). Layout owns completed geometry: it places the as-of line, so it completes the cone polygon from the as-of x and the plot, clipped to the plot. Scene completes paint: the gradient endpoints from the polygon's bounds, the stop opacities, the omission ladder; adapters serialize the completed gradient and decide nothing. The contrast and perceptibility gates read the completed Scene only.

### Data and resource model, migration

One optional Theme role and two optional role properties (`coneSpread`, `coneExtent`), added in place to `theme-v0.11` and `theme-v0.13` (Spec 56 section 3.2, S0 gate recorded in the PR). One optional field on the completed `LinearGradient` (`stop_opacities`), serialized in `scene-v0.7` in place; a Scene that carries it is written as v0.7, v0.6 is not edited. No resource migration, no committed Theme, preset or catalogue changes.

### Design review questions

1. Is a Symbol polygon with a gradient the right carrier, and does Layout-side clipping to the plot make a clip primitive unnecessary?
2. Does stop opacity belong on the gradient (a completed fact the ladder already governs) rather than in an ad hoc cone paint?
3. Is the cone as a non-ground to `_ground_under`, composited explicitly, sound for marks, state text and ground text, and does it never relax a floor?
4. Is the default output unchanged by construction (no role, no property, no emission, no field written)?
5. Does the omission remove the whole cone under the baseline so that no flat ink polygon can ever result?

### Acceptance evidence

Synthetic tests with no `examples/` input (Layout geometry and order, Scene paint and ladder, contrast ground, serialization and schema, SVG and a PNG raster check, determinism, default byte identity, baseline omission and failure); mutation checks of every rule; the S0 gate output; rendered SVG and PNG of the evidence slide read in full; the corpus contrast report (0 errors); conformance and the public materializers; the exact-main three-OS run on the review commit.

### Order of design slices

1. **D890-1** (this PR): baseline, design plan, design, architecture review and implementation plan together.
2. **I890-1**: code, specifications, evidence slide.
3. **A890**: acceptance review.

## 5. Design

Each decision is an owner-level judgement recorded on the issue with options, choice, reason and how to reverse it.

### 5.1 The primitive: a Symbol polygon, clipped by Layout (D1)

Option A: a filled polygon `Symbol` with a gradient, its outline completed by Layout and clipped to the plot rectangle in Layout. Option B: a gradient `Rect` over the plot plus a polygon clip. Choice: A. A Symbol is already the filled-polygon primitive, SVG and PNG draw it today, and the baseline admits it. B needs a clip that the Scene only has for a hosted Rect (`clip_source_id`), a second primitive for the clip host and a wider gradient box, and it would still leave the adapter to intersect. Layout can clip a convex polygon exactly. Reverse: emit a Rect and a clip host; Layout and Scene change in one place each.

### 5.2 Ink to transparent: stop opacity on the gradient (D2)

Option A: an optional per-stop opacity on the completed `LinearGradient` (`stop_opacities`, one value per stop), drawn as `stop-opacity`. Option B: an end stop coloured as the ground; wrong, because the ground differs under every band and texture. Option C: the primitive's single `opacity`; no fade. Choice: A. It is a completed paint fact, so the ladder (fidelity, capability `paint.linear-gradient`, omission) governs it unchanged, resvg and every SVG renderer honour `stop-opacity`, and the field is a plain additive Scene v0.7 member. Theme exposure is only through the cone role in this issue; a general `gradientStartOpacity` and `gradientEndOpacity` pair on every gradient role is the extension point (recorded in section 6), not built. Reverse: drop the field and keep a flat translucent cone.

### 5.3 Authoring: the Theme role `as-of-cone` (D3)

A Theme declares the role `as-of-cone` with `fill` (the ink, a Colour Scheme binding), `opacity` (the strength at the apex, `0..1`, optional, absent means 1), `coneSpread`, `coneExtent` (named number tokens) and `gradientFidelity` (existing property; absent means `required`, like every other treatment). Absent role means absent cone; there is no `none` spelling. The cone is drawn when the Theme declares it and the View shows an as-of marker (the View has no cone switch: appearance is the Theme's, as for the glow and the texture). A role without `fill`, `coneSpread` or `coneExtent` fails with `E_THEME_ROLE_REQUIRED` at the exact property pointer; a value out of range is `E_VISUAL_CAPABILITY_LIMIT`; any other property is `E_THEME_ROLE_PROPERTY_UNSUPPORTED` (the role contract admits `fill`, `opacity`, `coneSpread`, `coneExtent`, `gradientFidelity` only). Reverse: a View `asOf.cone` switch would be a View schema change; not needed.

### 5.4 Geometry (D4)

The apex is the top of the as-of line (the as-of x, the plot top). The cone widens downward to a foot at depth `coneExtent` times the plot height (`0 < extent <= 1`; 1 reaches the last row, the plot bottom of #880). `coneSpread` is the half-width gained per unit of depth, a ratio (`0 < spread <= 4`; 0.25 is a beam about 14 degrees to each side): a ratio, not an angle, so Layout needs no trigonometry and the polygon is bit-for-bit reproducible across the three operating systems. The triangle (apex, foot left, foot right) is clipped in Layout to the plot's inline extent (Sutherland-Hodgman against the two vertical edges; the block extent is already inside), coordinates rounded to 1/1000 px, vertices in a fixed order from the apex. A polygon with no area (the clip leaves nothing) gives no cone. The cone follows the line: no `as-of` placement, no cone.

### 5.5 Order and obstacles (D5)

The cone is a Layout shape with paint order 50: above the row, group, calendar and period bands (10 to 12) and the axis rules, below every mark (100 and up), the as-of line itself (100) and all hosted and foreground text (200, 300). The order is a rule of the shape, not of the Theme (the role admits no `backgroundPaintOrder`), so "beneath the marks" holds whatever a Theme gives a mark. A Theme can still give a band a higher `backgroundPaintOrder`, and then the band covers the cone, which the gate follows (5.6). The cone does not enter the obstacle inventory: it is a ground, like the bands, and labels and routes are free to cross it.

### 5.6 Ground rule for the gates (D6)

The cone is a translucent overlay, so it is never an ordinary opaque host. `contrast_policy._ground_under` skips it (role `as-of-cone`), and an explicit step composites it over the host the primitive truly lies on: for a classified mark, state text or ground text (not a decoration, which is a tint judged on the dominant substrate), the cone applies when it is later than the host in paint order and earlier than the primitive. The gradient is linear and the polygon convex, so the **worst ground over the stops the primitive spans** is found at the two ends of the primitive's block extent inside the gradient range: at each end where the primitive's box meets the cone's chord, the ground is the host colour with the cone ink composited at the strength the gradient has there (`opacity` times the stop opacity). A primitive that lies wholly inside the cone is judged on the blended grounds only; one that straddles the edge is also judged on the unblended host. The finding keeps one finding per channel, reports the worse ratio, the cone's identifier as `groundId`, the blended colour as `groundColor` and `groundKind` `cone-blend`. A canvas texture's or pattern's two colours are each blended. No floor changes and no diagnostic is relaxed: the cone only adds grounds, and a Theme whose bars become unreadable under a strong cone is fixed in its YAML. The cone has no contrast floor of its own and no class (a faint light is the point, and an unclassified decoration forces no corpus witness). `perceptibility`: the cone never raises `E_SCENE_TEXT_OCCLUDED` (it is translucent and below every text), and `I_SCENE_PAINT_CONTRAST` observes it at its apex strength.

### 5.7 Omission ladder and capability (D7)

The cone is gradient paint, so it needs `paint.linear-gradient`; no new capability ID. The Scene resolver completes it only when the selected profile admits the gradient. Under a profile that does not (the baseline), a `decorative-optional` cone is **omitted entirely** (no primitive; a flat polygon at the cone's ink would hide the plot) and reported as `I_VISUAL_TREATMENT_OMITTED:role=as-of-cone;treatment=as-of-cone;profile=<selected>;paintable=<first rich profile of the target>`; a `required` cone (the default when `gradientFidelity` is absent) fails before serialization with `E_VISUAL_CAPABILITY_UNSUPPORTED` at `/body/roles/as-of-cone/coneSpread`. The treatment name `as-of-cone` joins `PaintOmission`'s closed set. A shipped Draft preset may declare a cone `decorative-optional`: the omitted form (no cone) is a complete visible treatment. Reverse: none needed.

### 5.8 Adapters and Scene version (D8)

SVG draws the existing `<linearGradient>` with `stop-opacity` on each stop when the gradient carries stop opacities (the gradient id includes them; a gradient without them is byte-identical to today). PNG is the same SVG through the pinned resvg; both are rendered and read. PDF, Typst and TikZ never receive a gradient: the profile gate decides, never the adapter. Scene serialization writes `stopOpacities` on a gradient that has them and writes the Scene as v0.7 (the glow precedent); `scene-v0.7.schema.yaml` gains the optional member in place; v0.6 is the transitioning schema and is not edited.

### 5.9 Committed evidence (D9)

Controller Z (`examples/controller-z/`) gains the slide `as-of-cone`: the dark `title-card-dark` scheme, a Theme that declares the cone in a warm accent plus a label chip so the as-of label stays legible on the light, the executive View and Layout Profile, rendered under the rich SVG profile. No existing slide, preset or corpus datum is edited. It is evidence against the Marquee target, not a core criterion; the synthetic tests are the core criterion.

## 6. Architecture review

- **Ownership.** Theme declares; Layout completes the polygon and its order beside the as-of line it already places; Scene completes the gradient and the omission and owns the gradient's stop opacity; the adapter serializes completed values; the gates read the completed Scene. No new back channel from Layout to Scene beyond one more `ShapePlacement`.
- **Layering.** `layout/as_of_cone.py` imports Layout model types only; `scene` imports nothing new from Layout; `tools/check_import_direction.py` is expected to stay green.
- **Default output.** No role, property, shape, emission, gradient field or filter is written unless declared; every committed Scene and SVG must stay byte-identical (evidence of "default unchanged" only, not of quality).
- **Regression surface.** Layout composer (one call), registry (one binding), role contract and Theme resolution (one role), Scene builder (one emission and one paint branch), `LinearGradient` (one trailing field), `PaintOmission` (one treatment name), serialization and schema (one optional member), SVG (one conditional attribute), contrast policy (one skip and one composite step). The existing gradient path is untouched when `stop_opacities` is absent.
- **Failure behaviour.** Existing codes at exact Theme pointers (`E_THEME_ROLE_REQUIRED`, `E_THEME_ROLE_PROPERTY_UNSUPPORTED`, `E_VISUAL_CAPABILITY_LIMIT`, `E_VISUAL_CAPABILITY_FIDELITY`, `E_VISUAL_CAPABILITY_UNSUPPORTED`); no new code. An out-of-range spread or extent fails closed; a polygon with no area gives no cone, never a partial one.
- **Adjacent designs.** #587 (ladder, glow, texture ground), #880 (plot extent), #884 and #950 (ground rule extended with one more composited ground, no relaxed floor), #428 (the chip keeps the label legible; the as-of label itself stays unclassified, a pre-existing property), #893 (calendar shading adds bands at order 10 to 12 below the cone), #889 (region frames add their own order above), Spec 56 section 3.2.
- **Risks.** (1) A strong cone under an unclassified free label (the as-of label, an outside member label) is not gated, as before: classifying free text is a separate decision (disclosed; the evidence slide uses a chip). (2) A mark at the cone edge is judged on both grounds, so a Theme may need a darker outline; that is the correct strictness. (3) A band with a high `backgroundPaintOrder` covers the cone; the gate follows the paint order. (4) The Scene gains a field used by one role; a general stop-opacity Theme surface is the extension point and is not designed here.
- **Extension points.** `gradientStartOpacity` and `gradientEndOpacity` on any gradient role; a cone from a different marker (a deadline, a period edge) reuses the same polygon completion; a radial or curved light stays outside the closed vocabulary (Spec 63).
- **Decision:** approved for implementation planning.

## 7. Implementation plan

One code publication, `Refs #890`, default output unchanged. Generated Scene and SVG evidence of a committed slide is produced by the derived sync after the merge (CI rejects PR edits to manifest-declared evidence); locally it is regenerated into a scratch directory with `tools/regenerate_public_examples.py` to be inspected.

### I890-1: the cone

- **Files.**
  - `src/chrona/presentation/layout/as_of_cone.py` (new): `complete_as_of_cone(theme_tokens, plot, x)`; nothing without the role; geometry of 5.4; paint order 50.
  - `src/chrona/presentation/layout/surface_composer.py`: one call after the `as-of` placement.
  - `src/chrona/presentation/model/semantic_registry.py`: `asOfCone` (decoration, no contrast class).
  - `src/chrona/presentation/scene/capabilities.py`: role contract for `as-of-cone`; `coneSpread`, `coneExtent` classified as Layout geometry.
  - `src/chrona/presentation/color_scheme.py`: structural check of the role at resolution (5.3).
  - `src/chrona/presentation/scene/model.py`: `LinearGradient.stop_opacities`. `scene/paint.py`: cone paint resolution and the ladder. `scene/v05_builder.py`: emit the Symbol; omit under the baseline. `model/info_diagnostics.py`: the `as-of-cone` treatment. `usecases/diagnostic_messages.py` if a message enumerates treatments.
  - `src/chrona/presentation/scene/serialization.py` and `schemas/scene-v0.7.schema.yaml`: `stopOpacities`, version choice. `schemas/theme-v0.11.schema.yaml`, `schemas/theme-v0.13.schema.yaml`: `coneSpread`, `coneExtent`, in place; `conformance/schema-equivalence/expected-deltas-v0.1.yaml`: entries for them; the S0 result is recorded.
  - `src/chrona/presentation/renderers/v05_svg.py`: `stop-opacity`.
  - `src/chrona/presentation/scene/paint_analysis.py`, `contrast_policy.py`, `perceptibility.py`: the ground rule of 5.6.
  - `tools/check_scene_primitive_delivery.py`: the new gradient field.
  - `docs/specification/07-style-and-theme.md`, `08-scene-and-rendering.md`, `46-completed-scene-paint.md`, `63-portable-visual-capabilities.md`.
  - Controller Z: `themes/as-of-cone.yaml`, `contexts/as-of-cone.yaml`, a manifest entry; counting tests that grow with the corpus (as for #587).
  - Not touched: presets, catalogues, corpus data, the #585, #893, #889 and #882 files.
- **Tests (synthetic, no `examples/` input).**
  - `tests/unit/chrona/presentation/layout/test_as_of_cone.py`: absent role gives nothing; the apex is the line's top; foot depth is extent times plot height; half-width at the foot is spread times depth; clipped to the plot's inline extent on both sides; ends at the plot bottom when the plot is shorter than the slot (#880); no as-of, no cone; limits and missing properties; paint order between the bands and the marks; rounding and determinism.
  - `tests/unit/chrona/presentation/scene/test_as_of_cone_scene.py`: gradient endpoints from the bounds, stop opacities `(1, 0)`, strength as paint opacity; the ladder (baseline decorative-optional omitted with the typed diagnostic and no primitive, required fails with the pointer, rich profile paints, fidelity and limit failures); role admission (other properties rejected); the contrast ground: a mark inside the cone is judged on the blended ground at the stops it spans (worse of two), a mark outside is unchanged, a straddling mark counts both, a host later than the cone hides it, a state text and a ground text are covered, a decoration is not, a texture's two colours are each blended; serialization to v0.7 and schema validity; a v0.6 Scene unchanged.
  - `tests/integration/test_as_of_cone_render.py`: through `tests/support/synthetic_review.py` with the packaged `executive-light` bundle: SVG has the gradient with `stop-opacity` and the cone path drawn after the bands and before the first mark and every in-plot text; PNG (resvg) pixels: tinted near the apex, fading toward the foot, untouched outside the cone and below the foot; two renders byte-identical; a Theme without the role byte-identical to the render before the change; baseline omission and failure; Typst and TikZ never receive a gradient.
- **Mutation checks.** Each rule is run against a deliberately broken implementation and must fail: apex at the foot; spread unit; no clip; foot past the last row; paint order above marks or below bands; ignore extent; flat opacity (no stop opacities); fade reversed; cone as an ordinary ground; cone ignored by the gate; best instead of worst stop; straddling mark judged on the cone only; host later than the cone still blended; baseline paints a flat polygon; omission dropped; required passes; stop opacities dropped in SVG, or not in the gradient id; v0.6 written with the field. Results are listed in the PR.
- **Committed evidence.** The Controller Z slide of 5.9; SVG and PNG are read in full; the rest of the corpus is byte-identical; the corpus contrast report has 0 errors.
- **Acceptance gates.** Focused tests, the neighbouring suites (scene, layout, closure, role admission, serialization, schemas), `conformance/run_conformance.py`, `tools/check_import_direction.py`, `tools/regenerate_public_examples.py --check`, the S0 gate result, and the PR checks including `derived-ready`.
- **Publication boundary.** One PR; merged with the merge lock; the acceptance review bases on the derived-sync bot commit that follows it.

### A890: acceptance

`docs/reviews/current/issue-890-as-of-light-cone-acceptance-review-<date>.md` with the `chrona:literal-acceptance/v1` marker and one row per literal criterion; any narrowed row names a successor issue found by a duplicate search; checked by `tools/check_issue_acceptance_reviews.py`; merged; the exact-main three-OS run on the review commit located; #890 closed only when every row is met or narrowed with a successor and that run is green.
