# Issue #848: vector artwork behind an annotation container (work record)

Living record for [#848](https://github.com/tya5/chrona/issues/848) (Depth B, P4-A on the [#454](https://github.com/tya5/chrona/issues/454) board, read only; successor of #718, reopened by the reviewer because it was closed with no work done): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #848 (options, choice, why, how to reverse).

**Public base:** `528377f4` on `main`. **Status:** design plan, design, architecture review and implementation plan are published together in this one docs PR before any code. Slices A848-1 (gate) and A848-2 (mechanism and evidence) follow, each its own code PR (section 7).

## 1. Published baseline

#848 has the body below and one comment (the reopening). Read on `528377f4` from code, Specifications 07, 08, 46, 64 and the records of #465, #584, #718, #889, #950/#884, #980 and #1013:

1. **The container admits PNG only.** `ThemeTokenView.annotation_container` (`model/theme_tokens.py`) accepts `outline` `rectangle`, `balloon` or `image`; `image` names a raster icon-catalogue entry and declares `sliceInsetsEm` and `contentInsetEm` (#465). Layout (`layout/surface_annotations.py`) measures text into the content box, grows the paint box by the inset and tiles the raster with `image_slice_tiles`; Scene carries `paint.image`. Bundled catalogues are vector-only (#715 decision B), so no packaged part can be a backdrop. `rectangle` and `balloon` also accept `contentInsetEm` since #991.
2. **The parts exist and carry no colour.** `chrona-target-parts-v2026-10` (#718) has `scroll-frame` (48 x 64, six parts: hanger cord, two rods with knobs, a frame ring whose inner hole is the paper, mounting rings) and `clipping-edge` (64 x 8, one filled deckled ribbon), plus `panel-corner`, `bulb`, `hazard-tab`, `seal-*`. A glyph is a viewport and parts that are `fill` or `stroke` (a stroke part carries width, cap, join) with `M L Q Z` data, never both, no colour. The scroll's paper is a hole in its frame: the substrate under the artwork is what shows through.
3. **A glyph already reaches Layout and Scene.** `layout/mark_geometry.symbol_parts` fits a glyph (contain, centred) into bounds and completes `PathCommand` parts; the #584 stamp places them as one `ShapePlacement` of kind `Glyph` and Scene emits one `Symbol` per part (`v05_builder._symbol_primitives`, role paint from `annotation-kind-stamp`, `glyph_paint_mode`). `annotation_tilt.rotate_shape` already rotates a `Glyph` shape's parts.
4. **An annotation container is paint only.** The box is one `Rect` (or a `Symbol` for a balloon or a tilt) at paint order 400; the kind frame (accent, bar, stamp) follows at 400; text is 401 and above.
5. **The gate resolves grounds from the serialized Scene** (`scene/contrast_policy.py`): the topmost earlier opaque `Rect` or `Symbol` that covers the sample point by **bounds**, composited when translucent (#1013), a canvas texture or catalogue pattern host adding its ink as a second ground (#587, #884), a cone as a tint (#890); note prose lies only on its own same-source opaque flat `annotation-note-box` (C4, #950). `_SIBLING_INK_ROLES` stops sibling parts of one stamp being each other's ground. Classes are #995's: text and marks block, a decoration warns.
6. **Profiles.** Baseline admits `SYMBOL_OUTLINE`, not `LINE_CAP`/`LINE_JOIN`; a stroke part of a glyph carries a required finish, so a stamp with stroke parts fails `E_VISUAL_CAPABILITY_UNSUPPORTED` under baseline. A role property `<x>Fidelity` of `required` or `decorative-optional` already decides fail versus omit-and-report for gradients, glow and wobble (`paint._admit`, `PaintOmission`). Typst rejects every `Symbol` (`render_v05_typst`); TikZ draws a `Symbol` as a filled path only.
7. **The targets.** Yuya's hanging scroll behind each note and Marquee's newspaper clipping (a deckled edge) are the two named evidence cases; Tenth Frame frames and Off-World printouts name the same mechanism (`docs/research/presentation/*-target-2026-09-26/README.md`).

Inferred, not read: how the scroll looks when stretched (its hanger cord sits in the stretched top-centre cell). Unverified until A848-2: the rendered result (read as an image), how TikZ treats a stroke-only part, and whether the perceptibility checks accept a backdrop part whose bounds cover its text.

## 2. Literal acceptance (copied from the issue)

1. A packaged vector asset can be the backdrop of an annotation container, stretched to its content, with the text measured into the content area and checked for contrast against the backdrop's content ground.
2. Evidence: a scroll and a clipping through YAML, with the packaged parts of #718.

Assignment constraints, kept as rows of the acceptance review: (3) a general Theme declaration with size and inset rules, tilt compatibility and ordering under text; (4) the artwork's ink and substrate are grounds for the text over it, through the gate's existing ground resolution; (5) determinism; (6) the baseline-profile omission ladder, and what Typst and TikZ do, stated honestly; (7) defaults leave every output unchanged; (8) synthetic tests with no `examples/` input, mutation-checked, no corpus datum edited, the rendered images read, the evidence slide on Controller Z and not on `examples/halcyon-1/*target-b*`; (9) the S0 schema gate result; (10) owner-level decisions recorded on the issue.

## 3. Dependencies and neighbours

- Reused unchanged: #465 (nine-slice vocabulary, content inset, `image_slice_tiles` stays for rasters), #584 (kind frame, tilt, `rotate_shape`, stamp emission), #718 (the parts, not edited), #991 (`contentInsetEm` on a rectangle), #889/#1013/#950/#980/#995 (ground resolution and severity classes).
- Other agents: #991 (ghost, hatch, comparison code), #1030/#1031 (relation routing), #911 (`presets/*.yaml`). No file of theirs is touched. The reviewer's `examples/halcyon-1/*target-b*` is not edited; evidence goes on Controller Z.
- Shared files kept minimal: `schemas/theme-v0.13.schema.yaml`, `theme-v0.11.schema.yaml`, `conformance/schema-equivalence/expected-deltas-v0.1.yaml`, Specifications 07, 08, 46, the controller-z manifest, the public-slide count tests. #453/#454 are read only.

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A note sits on a packaged hanging scroll: rods top and bottom keep their size, the frame grows with the text, the text lies in the paper. | Yuya, #848 |
| U2 | A note is a newspaper clipping: a deckled edge strip stretched along one side of the note. | Marquee, #848 |
| U3 | The same declaration serves a frame, a corner bracket or a pattern-like glyph (`panel-corner`, `hazard-tab`) for other targets. | Tenth Frame, Off-World |
| U4 | A tilted note carries its artwork rigidly; a kind header, bar, accent and stamp sit inside it. | #584 |
| U5 | The text over the artwork is judged on the substrate and on any artwork ink it actually touches. | #884, #950, #1013 |
| U6 | Under a profile that cannot paint the artwork the Theme chooses to fail or to omit it; geometry never changes with the profile. | #588, #890 |
| U7 | Every existing Theme and View renders unchanged. | all |

Open decisions (closed in section 5, recorded on #848): **D1** one glyph with nine-slice versus several glyph parts placed by Layout; **D2** where the declaration lives; **D3** the scale and the unit of the insets; **D4** who paints the ink; **D5** paint order and what the artwork may cover; **D6** contrast grounds; **D7** the omission ladder and adapters; **D8** tilt; **D9** failure codes.

Responsibility boundary: Theme declares glyph, insets, unit and ink; Layout reads Theme and the pinned glyph, warps and completes the parts and the paint box; Scene carries completed `Symbol` parts and paint; the gate reads the serialized Scene alone; adapters serialize. Data model: one optional object on the existing `annotationContainer` token, one optional role, no Scene member, no View change. Migration: none. Design review questions: is the declaration one mechanism with the PNG form rather than a second one; does any default byte move; can the gate be fooled by a part whose bounds cover text it does not touch; is the profile ladder the established one; is the warp deterministic and exact.

Acceptance evidence planned: synthetic tests only (no `examples/` input; `tests/support/synthetic_review.py` plus the packaged parts), per rule a test and a mutation check, the rendered images of both targets' parts read in full, the S0 gate result, one Controller Z evidence slide per target through new Theme, View and Context YAML (the bot regenerates derived output), the literal acceptance review, the exact-main three-OS run.

## 5. Design

### 5.1 The declaration (D1, D2, D3)

**D1.** The artwork is **one catalogue glyph stretched by nine-slice with declared insets**, as the issue's first alternative and as the PNG path does. The second alternative (several glyph parts placed at corners and edges by Layout) is rejected here: it needs a placement vocabulary per part, and a corner part is a nine-slice with a fixed corner cell, so nine-slice covers it; a repeated border is #587's mechanism.

**D2.** The declaration is an optional property `artwork` of the `annotationContainer` token on the annotation-box role, admitted with `outline: rectangle` only:

```yaml
annotation-note-box:
  annotationContainer: container.scroll      # a token of type annotationContainer
container.scroll:
  type: annotationContainer
  value:
    outline: rectangle
    cornerRadius: 0
    contentInsetEm: {top: 1.8, right: 1.0, bottom: 1.4, left: 1.0}   # required with artwork
    artwork:
      glyph: "chrona-target-parts:scroll-frame"   # set:name, a catalogue glyph
      sliceInsets: {top: 16.3, right: 8.2, bottom: 11.5, left: 8.2}  # glyph viewport units
      unitEm: 0.09                                 # one viewport unit, in em of the note text
```

It is a property rather than a fourth `outline` value because the artwork is ink over a substrate the outline already describes: the box `Rect` keeps painting the paper (its fill is the content ground), composes with the tilt (rectangle only), the kind bar and accent (rectangle only, #584) and the #991 content inset, and `outline: image` already is a self-contained artwork. A balloon (its tail would pierce the frame) and an image outline with `artwork` are `E_THEME_TOKEN_TYPE` at the property, as `tiltDegrees` is. `contentInsetEm` is required with `artwork` (as for `image`): a framed note must say where its paper is. Rejected: `outline: glyph` (an unspecified substrate shape that would forbid the bar and the accent and duplicate the image form).

**D3, size and inset rules (all Layout).**

- `glyph` must be a catalogue glyph the pinned Context resolves (`E_THEME_ASSET_REFERENCE` at the closure pointer). `sliceInsets` are four non-negative numbers in the glyph's **viewport units** with `left + right <= inlineSize` and `top + bottom <= blockSize` (else `E_THEME_TOKEN_TYPE` at `.../artwork/sliceInsets`). `unitEm` is a finite number greater than zero: the size of one viewport unit in em of the annotation text size. Both are Theme facts, as `sliceInsetsEm` is for a PNG; the catalogue keeps carrying only geometry.
- **The artwork is stretched to the paint box**, the box Layout already searches and registers (text box plus `contentInsetEm`). Nothing about the artwork changes the box, the candidate search, the obstacles or the leader.
- **Fixed borders keep their authored size.** A border's destination size is its inset times `unitEm` times the text size; the three source columns (left inset, the middle, right inset) map to the three destination columns, likewise the rows. The map is piecewise linear and axis separable. When `left + right` (or `top + bottom`) of the destination exceeds the paint box, both borders scale down by one common factor, as `image_slice_tiles` does, so no cell inverts. A zero inset collapses that border: all four zero stretches the glyph over the whole box (the "stretched" case); `top` equal to the viewport height with the others zero fixes a strip to the top edge and stretches it along the inline axis (U2, the clipping edge, with `bottom` for the bottom edge).
- **The warp is exact for the glyph grammar.** A part is a path of `M`, `L`, `Q` and `Z`. Each `L` and `Q` is split at every cell boundary it crosses (a line at the intersection, a quadratic at the roots of the coordinate by de Casteljau), so each piece lies in one cell, where the map is affine and maps a line to a line and a quadratic to a quadratic. A hole stays a hole (winding is preserved). Stroke widths scale with `unitEm` times the text size and are not warped, so a rod's line weight is the same in every cell. The result is `SymbolPartPlacement`s with the glyph's paint mode, width, cap and join, as the stamp's.
- **The deliberate limit.** A nine-slice stretches the cells it declares: the scroll's hanger cord sits in the top-centre cell and widens with the note, as any three-slice scroll does. A glyph authored for stretch (hanger inside a fixed corner cell, or a wide fixed border) avoids it; no catalogue entry is edited here.

### 5.2 Paint, ordering and what the artwork may cover (D4, D5)

- **D4, the ink.** A new optional-by-default role `annotation-artwork` (semantic `annotationArtwork`, scene kind `Symbol`, class `DECORATION`) carries `fill` (fill parts), `stroke` (stroke parts, with the glyph's own width, cap and join), `opacity` and `artworkFidelity` (section 5.5). It is shared by every annotation purpose, like the kind roles. A container that declares `artwork` while the Theme has no `annotation-artwork` role is `E_THEME_ROLE_REQUIRED` at `/body/roles/annotation-artwork`, never a silent omission. The substrate is the box role's own fill, unchanged.
- **D5, order.** In the annotations slot: box (substrate, 400), then the artwork parts (400, emitted right after the box in part order), then the kind frame (accent, bar, stamp, 400), then all text (401 and above). The artwork is therefore under the bar, the accent, the stamp and every line of text, over the paper only. Its parts have the paint box as bounds.
- Without `artwork` Layout emits no shape and Scene no primitive: byte-identical output (U7).

### 5.3 Tilt (D8)

`artwork` is admitted with `outline: rectangle`, the only outline that tilts. Layout warps the glyph into the **unrotated** frame, then rotates the parts rigidly about the frame centre with the existing `rotate_shape` (a `Glyph` shape), with the box, the kind frame and the text; the search used the rotated extent already. A tilted note's artwork and text rotate as one body, so the rotation changes no overlap between them. The gate samples rotated geometry from the completed outlines.

### 5.4 Contrast (D6), through the gate's existing ground resolution

The artwork has a **substrate** (the box fill) and **ink** (the part colours): the pair the gate already resolves for a catalogue pattern host (`substrate` and `ink`, the worst decides, #587, #884) and for a translucent host (composited with `blend_over`, #1013). Two points need care, and they are the whole of A848-1:

1. **A part is not a host by bounds.** The parts' bounds are the paint box, so the generic rule (topmost earlier covering `Rect` or `Symbol`) would take the frame ring as the ground of every line of text inside its hole. A part with role `annotation-artwork` is never chosen as a host by bounds. The text's host is the box (the substrate) or the bar, as today; note prose keeps C4, its own opaque flat box.
2. **Ink is a ground where it is touched.** For a label of the `legibility` class (state text, ground text, mark) whose `sourceRef` equals an earlier artwork part's, the gate adds that part's ink as one more ground **iff the painted area of the part meets the label's bounds**: for a fill part, any outline edge meets the bounds or the bounds lie inside the filled area (non-zero winding, so a hole is empty); for a stroke part, the flattened path comes within half the stroke width of the bounds. The ink is composited at the part's opacity over the box fill (the substrate). The label is judged on every ground and the worst ratio decides, as for a pattern; the finding names the part (`groundId`), `groundKind` `artwork-ink`, and the colour. A label that touches no ink is judged on the substrate only. A decoration over the artwork (the bar) keeps the dominant-substrate model, no ink ground (#995).
3. **The artwork against its substrate** is judged by the existing `DECORATION` rule: each part against the box it lies on (floor 1.10, a warning unless the Theme asks for an error). The parts of one artwork are one ink and never each other's ground, because a part is never a host by bounds (point 1), so no sibling exemption is needed.

A Theme author who leaves the content inset too small so that text touches the frame is therefore told so by a blocking `E_SCENE_STATE_TEXT_CONTRAST` when the text is illegible on the ink, and passes when it is legible on both: Layout never judges, and no corpus-sized allowance is added. What stays unresolvable stays as Specification 46 section 8 lists it (a translucent box under note prose, an unreadable paint).

### 5.5 Profiles, adapters, omission ladder (D7)

A fill part needs `SYMBOL_OUTLINE`, which baseline admits. A stroke part carries a required line cap and join, so it needs `LINE_CAP` and `LINE_JOIN`, which the rich SVG and PNG profiles admit. The role property `artworkFidelity` (token type `fidelity`, default `required`, as `gradientFidelity`) decides, in Scene and with no Layout input:

1. **Rich SVG/PNG profile:** every part is painted.
2. **A profile without cap/join and a glyph with a stroke part:** `required` fails with `E_VISUAL_CAPABILITY_UNSUPPORTED` at `/body/roles/annotation-artwork/artworkFidelity` (the first supporting profile is suggested, as for any treatment); `decorative-optional` omits the **whole artwork** (never a frame with its rods dropped), reports one `PaintOmission` (role `annotation-artwork`, treatment `annotation-artwork`) and leaves the box, the text and every Layout fact exactly as with the artwork. A fill-only glyph (the clipping edge) needs no omission under baseline.
3. **Typst:** rejects every `Symbol` with `E_VISUAL_CAPABILITY_UNSUPPORTED` (as for a balloon, a tilt or a stamp). A fully omitted artwork leaves no Symbol, so a baseline-profile `decorative-optional` render of a plain rectangle note still compiles; an artwork that is drawn is rejected. No Typst drawing of artwork is shipped.
4. **TikZ:** draws a `Symbol` as a filled path (fill parts of the artwork). Stroke parts: verified in A848-2 against the adapter and recorded here with its result (the adapter is not changed by this issue); if TikZ cannot draw a stroke-only `Symbol`, it fails closed, never silently.
5. **PDF** is derived from the SVG route and is not verified separately.

Geometry never depends on the profile: the omitted artwork occupies no space it did not have.

### 5.6 Determinism

The warp is closed-form arithmetic over the declared numbers, the glyph data and the paint box: no random source, hash, clock or iteration order; split points are taken in a fixed order (cell boundaries ascending along the segment). Two renders are byte-equal, and the same declaration under a tilt cycle (#584) is deterministic by that rule.

### 5.7 Failure behaviour

| Condition | Code | Raised at |
| --- | --- | --- |
| `artwork` on a balloon or image outline; `artwork` without `contentInsetEm`; a malformed object; `unitEm` not above zero; a negative or non-numeric inset | `E_THEME_TOKEN_TYPE` (and the live Theme schema) | `/body/roles/<role>/annotationContainer/artwork...` |
| Insets larger than the glyph viewport | `E_THEME_TOKEN_TYPE` | `.../artwork/sliceInsets` |
| Unknown glyph or unpinned set | `E_THEME_ASSET_REFERENCE` (existing) | Closure, `/body/values/<token>/value/artwork/glyph` |
| `artwork` without the role `annotation-artwork` | `E_THEME_ROLE_REQUIRED` (existing) | `/body/roles/annotation-artwork` |
| Stroke part under a profile without cap/join, `required` | `E_VISUAL_CAPABILITY_UNSUPPORTED` (existing) | Scene paint |
| Text illegible on the substrate or on touched ink | `E_SCENE_STATE_TEXT_CONTRAST` (existing) | Scene gate |
| Artwork ink under 1.10 against its substrate | `W_SCENE_DECORATION_CONTRAST` (existing, #995) | Scene gate |

No new diagnostic code is introduced; each failure is a declaration conflict, never a dropped or substituted artwork.

## 6. Architecture review

- **View selects, Theme paints, Layout places.** The View is untouched. The Theme declares glyph, insets, unit and ink; Layout reads Theme strings, numbers and the pinned glyph and completes every part; Scene carries completed `Symbol` parts and paint; the gate reads the serialized Scene alone; adapters serialize. The warp is Layout's (it is geometry); the omission is Scene's (it needs the profile), as for every other optional treatment.
- **One mechanism.** The nine-slice vocabulary, the content inset, the paint box, the glyph fit, the stamp emission, the tilt rotation, the pattern-host ground, the composite and the fidelity ladder are all reused. The new code is the warp (pure), the ink-touch test (pure) and registrations. The PNG path is not touched and still serves rasters.
- **Specification 56 section 3.2.** Behaviour-preserving optional additions in place, no version bump: `artwork` in the `annotationContainer` token value and the `artworkFidelity` role property in `theme-v0.13` and the transitioning `theme-v0.11`, as #584 did for `tiltDegrees`; the role registers in the capability table. Every schema PR runs `python -m tools.schema_equivalence --base-rev origin/main`, records the result, follows `--prune-stale` guidance and keeps its own expected-delta entries correct (the gate ages entries from git history, #970). A schema `default` implements nothing at runtime.
- **Adjacent designs.** #465 (an image outline is its own artwork; `artwork` is rectangle only), #584 (bar and accent are rectangle only, so they compose; the kind text is judged by the same rules), #991 (the inset), #1013 (composite over the substrate), #950/C4 (note prose keeps its own box pairing), #995 (decoration warns, text blocks), #587/#884 (ink and substrate), #889 (a region frame is a different, Layout-owned frame of a slot; nothing shared), #718 (data, not edited).
- **Gate soundness.** The risk is a verdict better or worse than the truth. A bounds-only ink test would flag the scroll's text for the ring that surrounds it; exact geometry does not. A missed touch would let illegible text pass: the test is conservative at the stroke (half width, caps ignored by padding), exact at fills up to the flattening of a quadratic (eight segments per curve, bounded error stated in the tests), and mutation-checked both ways.
- **Byte identity.** Without `artwork` and the role, Layout and Scene run no new branch. Regenerating the public slides is evidence of that only, not a quality bar; the behaviour is proven on synthetic fixtures and rendered images.
- **Corpus is evidence, not an oracle.** No corpus datum, Theme, Scene or report is edited to pass a criterion; the evidence slides are new YAML on an existing Project.
- **Rejected options.** Several glyph parts placed at corners by Layout (D1); `outline: glyph` (D2); insets in em with a 1:1 source (no natural pixel for a vector); a scale fitted to the box height (no stable fixed border); per-part bounds as hosts or as grounds (false verdicts); a Layout hard error when the inset touches the ink (judgement belongs to the gate, and legible text over ink is valid); a Typst or TikZ stroke drawing without verification; a catalogue edit; absorbing #849 or #587.
- **Owner-level judgement calls** (options, choice, why, reversal on the issue): D1 one glyph with nine-slice; D2 a property on the rectangle container; D3 `unitEm` with viewport-unit insets and the warp rule; D4 a shared `annotation-artwork` role; D6 ink as a ground where touched, by exact geometry; D7 whole-artwork omission with `artworkFidelity`.
- **Extension points (not designed here, successors if wanted):** a per-kind artwork, several artwork layers on one container (a clipping with both edges), a repeated-glyph border (#587), vertical/horizontal flip of a part, Typst and TikZ drawing of stroked artwork.

## 7. Implementation plan

Each code PR is `Refs #848`, leaves every committed example byte-identical for a document without the declaration, regenerates nothing by hand (the derived sync does), names its mutation checks and carries the S0 gate result when it touches a schema.

| Slice | Owned files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **A848-1, gate** | new pure `scene/ink_touch.py` (flatten `M L Q`, non-zero winding, rectangle against fill and against stroke); `scene/contrast_policy.py` (artwork parts are never hosts by bounds; the ink-touch ground group; `annotation-artwork` in `_SIBLING_INK_ROLES`); Specifications 46 and 08 | hand-built Scenes: a frame ring with text in its hole judged on the substrate only; text touching the ring judged on the ink (pass and fail); a stroke part; a translucent ink composite; a part is no host; the bar over artwork keeps the substrate model; a hole is empty; determinism. Mutations: bounds instead of geometry, hole filled, stroke half-width dropped or doubled, ink ignored, opacity ignored, another note's artwork, a later part, a decoration given ink, an unreadable part skipped | none | one code PR; dead without artwork primitives, so no output moves |
| **A848-2, mechanism and evidence** | new pure `layout/glyph_slice_geometry.py` (the warp); `model/theme_tokens.py` (`artwork` in the container token and its validation); `model/closure.py` (resolve the glyph); `model/semantic_registry.py`, `scene/capabilities.py` (role `annotation-artwork`, `artworkFidelity`); `layout/surface_annotations.py` and `layout/surface_quality.py` (the `Glyph` shape after the box, tilt rotation); `scene/v05_builder.py` and `scene/paint.py` (emission, omission ladder); `schemas/theme-v0.13.schema.yaml`, `theme-v0.11.schema.yaml`, `conformance/schema-equivalence/expected-deltas-v0.1.yaml`; Specifications 07, 08 (and 64 section 7: the vector use); the Controller Z Theme, View, Context and manifest entry per target; the public-slide count tests; `docs/research/presentation/*` README status rows for yuya and marquee | warp unit tests (identity at the glyph's own size, each border fixed, middle stretched, a box smaller than the borders, zero insets, strip fixed to an edge, a line and a quadratic crossing a boundary split exactly, a hole kept, stroke width scaled by `unitEm`, determinism); Theme token tests for every rejection; integration through `tests/support/synthetic_review.py`: default byte-equal to the base render, the scroll and the clipping parts present and ordered box, artwork, kind frame, text; text inside the paint box; text measured into the content inset; box size and search unchanged by the artwork; tilt rotates artwork with the note; bar and accent over artwork; contrast on the substrate and on touched ink; the omission ladder under baseline (fail `required`, omit `decorative-optional` with one report, fill-only glyph kept); TikZ and Typst behaviour recorded; missing role; unknown glyph; balloon and image rejected. Mutations: slice cells swapped, borders not fixed, middle not stretched, boundary crossing not split, hole lost, stroke width unscaled, artwork before the box, artwork over the text, the artwork resizing the box, tilt not applied to artwork, partial omission, fidelity ignored, role requirement removed | the bot regenerates the two new slides and the reports | one code PR |
| **Acceptance** | `docs/reviews/current/issue-848-vector-artwork-acceptance-review-2026-10-03.md` | literal rows from section 2 | none | one docs PR, then the exact-main three-OS run |

**Evidence slides (A848-2).** New YAML on Controller Z (existing Project, no datum edited): `themes/annotation-artwork-scroll.yaml` and `-clipping.yaml` (or one Theme per target) pinning `chrona-target-parts`, with their Contexts and a View of notes; one manifest entry each. The images are read in full for both parts and for a tilted and a profile-omitted variant on synthetic slides. The reviewer's `examples/halcyon-1/*target-b*` is not touched.

**Mutation checks** are listed per slice above; each must fail at least one test, and a surviving mutation gets a new test before the PR is published.

**Order and risk.** If implementation shows a rule beyond section 5 is needed (for example a warp that cannot be exact for a glyph in the catalogue, or a perceptibility check rejecting a backdrop part), that slice stops, the cause is recorded here, the design is corrected and published before code resumes.

## 8. Progress and evidence

Design plan, design, architecture review and implementation plan published together (this document). No code yet.
