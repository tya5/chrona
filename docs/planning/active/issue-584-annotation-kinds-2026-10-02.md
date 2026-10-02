# Issue #584: annotation kinds, title bar, accent edge, stamp and a deterministic tilt (work record)

Living record for [#584](https://github.com/tya5/chrona/issues/584): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `99a52a83` on `main`. **Status:** design plan, design, architecture review and implementation plan are published together in this record (one docs PR); no code yet. Code slices A584-1 (kind header: title bar, accent edge), A584-2 (stamp) and A584-3 (tilt) follow, each default-output-unchanged.

## 1. Published baseline

Issue #584 has no comments before this work (body unchanged since filing). It is the P4-B annotations item of #453's gap map (read only). #718 (closed) packaged the parts; #848 (open, another owner) is vector artwork behind a container and is **not absorbed** here.

Read on `99a52a83`:

1. **An annotation container is paint only.** `layout/surface_annotations.py:place_annotations` places one box per annotation (`annotation-box:<id>`, a `Rect`, a `Balloon` path, or an image-filled `Rect` under #465), its text (`annotation-text:<id>`), optional label visuals, a numbered marker and a leader. Theme role paint is `annotation-<purpose>-box|text|leader` (`semantic_registry.py`); the geometry token is `annotationContainer` (`outline: rectangle|balloon|image`, `cornerRadius`, `tailBaseEm`, image insets), read by `ThemeTokenView.annotation_container`. There is no header, edge or mark inside the container.
2. **There are two vocabularies, and only one is a kind.** The View `purpose` is the closed four-value intent (`callout`, `highlight`, `note`, `explanatory-arrow`, `vocabulary-v0.1`) that drives placement and the box role. The **kind** is the Project annotation's `kind` (`project-v0.7` `annotation.kind`, an open string: HALCYON-1 has `note` and `risk`; Controller Z has `callout`). A View annotation reaches it through `projectAnnotation: <id>` (`v05_content.py:_annotation_text` already reads that Project note for its text). `AnnotationIntent` carries `purpose` but not the kind, so no layer downstream of content normalisation knows it. The HALCYON `02-programme-board` View gives all three notes `purpose: note` and distinguishes them only by Project kind, so a kind treatment cannot be keyed by purpose.
3. **Per-kind colour has a precedent.** `resolve_color_scale` (Specification 60) maps a value to a Scheme category colour through Theme `colorScales`; #583 reused it for a per-group tint and applied it as a completed Scene paint replacement keyed by `source_ref` (`render_review._resolve_group_tints`, `SurfaceContentInput.group_tints`, `v05_builder._complete_primitive_paint`). Layout never reads a Scheme.
4. **The contrast gates are role-keyed.** `contrast_policy.evaluate_scene_contrast` judges a classified role against the ground found under its sample point from earlier completed primitives; note prose is judged against its same-source `annotation-note-box` (`_note_box_ground`). `color_scheme._state_text_contrast` checks every declared state-text role against the Scheme `surface` at Theme resolution. The decoration witness (`tools/presentation_contrast.py`) requires every registered `DECORATION` role to be painted somewhere in committed public Scene evidence.
5. **Scene can rotate text by 90 degrees only.** `TextLayout.orientation` is `horizontal|rotate-cw|rotate-ccw` with `rotation_degrees` in `{0, 90, -90}` (`scene/model.py`, `scene-v0.7` `textLayout`); `v05_svg` writes `transform="rotate(deg x y)"` about the baseline start, TikZ writes `rotate=` on a `base west` node (the same pivot), Typst places a `top + left` rotation at the baseline and rejects every `Symbol` primitive. A tilted rectangle is representable as a closed `Symbol` path, as a balloon already is. Nothing rotates a box.
6. **Catalogue parts exist.** `chrona-target-parts:hazard-tab`, `seal-risk`, `seal-note` (kind corner and stamps) are packaged and consumed by nothing (#718 README); glyphs resolve through the pinned Context into a Layout-completed outline (`symbol` token, `{catalog: set:name}`).
7. **Theme additions are in place** (Specification 56 section 3.2): #492 `tickLength`, #587 `glow*` edited `theme-v0.11` and `theme-v0.13` with no version bump and one expected-delta entry each when the gate asked. Scene v0.7 gained `paint.glow` in place and is selected when a document carries it (`serialization.scene_document`).

Inferred, not read: which target needs which treatment (section 4 table, from the READMEs and the issue body, not from the mock images). Unverified until each slice: the rendered result (read as images), how header and stamp compose with a balloon or image outline, and the Typst route for a tilt (Typst already rejects `Symbol`).

## 2. Literal acceptance (copied from the issue)

1. Kind-keyed title bar, accent and stamp; synthetic tests cover each.
2. Rotated notes are placed by the #466 model using their rotated bounds. Rotation is deterministic, and contrast is checked on the rotated text.
3. Evidence: Title Card and Marquee notes on corpus slides through YAML.

## 3. Dependencies and neighbours

- #466 (annotation placement model), #465 (image container) and #496 (catalogue patterns and glyphs) are closed and supply the machinery used. #718 (closed) supplies the parts. #587 (closed) shares `theme-v0.13`/`theme-v0.11`, `capabilities.py` and `scene-v0.7`; this work edits only its own lines.
- **Not touched:** #848 (vector artwork behind a container; this work keeps a container's outline contract and adds nothing to `outline`), #813 (MCP mutating tools), #829 (diagnostic detail), #586 (derived header figures: `group_header_text.py`, group-header text, View `figures`; this work adds no View property and does not read that module). #453 and #454 are read only.
- Shared files, kept minimal: `schemas/theme-v0.13.schema.yaml` and `theme-v0.11.schema.yaml`, `schemas/scene-v0.7.schema.yaml` (slice 3), `schemas/schema-equivalence/expected-deltas-v0.1.yaml`, Specification 07 and 08, the controller-z or halcyon example manifests and the public-slide count tests (an evidence slide per slice).

## 4. Design plan

### Use cases

| Id | Use case | Targets |
| --- | --- | --- |
| U1 | A note whose Project kind is `risk` or `note` shows a header carrying the kind's label, optionally a secondary-script sub-line and the anchor subject (`警告` over `WARNING`; `RISK · payload-tvac`), in a coloured title bar | Title Card, Target B (2) |
| U2 | The same note carries a coloured accent edge on one side | Target B (1; also a Title Card variant) |
| U3 | The kind is also a stamp: a seal glyph (`危`/`記`) or a hazard corner chosen by kind, placed at a corner of the note | Yuya, Title Card (2) |
| U4 | Notes lean by a small, deterministic angle; the leaders, the search and the obstacles all use the rotated geometry | Marquee (1) |
| U5 | Every existing View, Theme and Layout renders unchanged | all |

### Slices, ordered by targets unlocked

1. **A584-1, kind header (U1, U2).** The kind reaches Layout; a Theme `annotationKinds` entry declares the label, the optional secondary label, the title template and the kind colour; Theme roles place the title bar, the header text and the accent edge. Unlocks Title Card (bar) and Target B (header text and accent): 2 targets, and every later slice depends on the kind plumbing.
2. **A584-2, stamp (U3).** A per-kind catalogue glyph in a reserved corner column. Unlocks Yuya and completes Title Card (hazard corner): 2 targets. Needs A584-1's kind data only.
3. **A584-3, tilt (U4).** Unlocks Marquee (1 target) and is the largest change (Layout rigid transform, Scene text rotation, rotated obstacles and leader ports), so it is last. Independent of A584-1/2 in code, but it must rotate whatever they add, so it follows them.
4. **Evidence (row 3).** Each slice adds one committed evidence slide through new Theme/Context YAML on an existing corpus Project and View (HALCYON-1 `02-programme-board`, kinds `risk` and `note`), editing no corpus datum. The registered `DECORATION` roles also need such a painted slide (the witness).

### Open decisions (closed in section 5)

- **D1 kind source.** Project `kind` through `projectAnnotation`, View `purpose`, or a new View field.
- **D2 where the per-kind declaration lives.** Theme object, View object, or per-purpose Theme roles.
- **D3 label text and grammar.** Closed template placeholders versus a fixed shape; where the secondary-script label goes.
- **D4 kind colour.** Scheme category through a Theme-declared colour, applied as completed Scene paint, versus per-kind roles.
- **D5 geometry.** What grows the box; how bar, accent, header text and (later) stamp compose; which outlines admit which treatment.
- **D6 contrast.** How the header text and the stamp are gated when the ground is a per-kind colour.
- **D7 stamp.** Glyph per kind, size, corner, the reserved space.
- **D8 tilt declaration.** View or Theme; none/fixed/alternation versus one cycle; bound; which outlines.
- **D9 tilt geometry.** Rotated bounds for search and obstacles, the leader port, text and Scene representation, adapters, interaction with header, accent, stamp and label visuals.
- **D10 evidence and slides.**

### Responsibility and architecture review questions

- Does the kind enter at content normalisation (View/Project facts), Layout read only Theme strings and geometry, and the kind colour reach Scene as a completed paint, so Layout reads no Scheme?
- Does one declaration per kind avoid a second vocabulary (purpose versus kind) and a role explosion?
- Does the header text get the same contrast discipline as note prose (a classified role judged against its real ground) without a wrong static check against the canvas?
- Is the tilt a Layout-completed rigid transform, with Scene carrying completed rotated geometry and no adapter deciding anything?
- Is every addition optional and removable (Specification 56 section 3.2) and is the default byte-identical?
- Does anything collide with #848, #586, #813 or #829?

### Acceptance evidence planned

Synthetic tests only (no `examples/` input; `tests/support/synthetic_review.py` plus the packaged bundle, as #583): per treatment, the default (no declaration) output equal to the base render, each rule, each failure, a rendered image read in full, a mutation check per rule. The S0 gate result in every schema PR. One evidence slide per slice through new YAML only. The literal acceptance review per section 2, `tools/check_issue_acceptance_reviews.py`, and the exact-main three-OS run.

### Order of publication

1. This record (one docs PR) with the owner-decision comment on #584. 2. A584-1, A584-2, A584-3 as separate code PRs, each `Refs #584`. 3. Acceptance review and the exact-main run.

## 5. Design

### 5.1 The kind and its declaration (D1, D2)

**Kind source (D1).** The kind of an annotation is the `kind` of the Project annotation its View annotation references (`projectAnnotation`). Content normalisation (`review/v05_content.py:_annotation`) sets a new `AnnotationIntent.kind: str | None` (default `None`); a View annotation with its own `text` has no kind and renders as today. Rejected: `purpose` (a closed placement intent, four values, and HALCYON's three notes share one); a new View `kind` property on `annotations[]` (duplicates a Project fact and edits the View schema other work is changing).

**Declaration (D2).** A Theme body gains an optional object `annotationKinds`, keyed by kind id:

```yaml
annotationKinds:
  risk:
    label: "警告"                          # required, non-empty
    secondary: "WARNING"                    # optional second-script label
    title: "{label}"                        # optional template, default "{label}"
    color: "category:alert"                 # optional: a Scheme intent or an explicit category slot
    stamp: "chrona-target-parts:seal-risk"  # A584-2
  note:
    label: "報告"
    secondary: "REPORT"
    color: "category:report"
```

A kind that the Theme does not declare gets no kind treatment (an open vocabulary: a Theme chooses which kinds it dresses; this is the default, not a fallback colour). A Theme without `annotationKinds`, or a Project without a kind, is today's output.

Why the Theme (judgement call, recorded on the issue): the words, the colour and the glyph that say "this is a risk" are a target's presentation vocabulary (Title Card says `警告 WARNING`, Target B says `RISK`, Yuya a seal) for one Project fact, not a function of data that varies per note, so they live with the appearance that uses them; the template stays a closed string. This differs from #583 (group header text, a template over per-group data and an entity field) deliberately. Reversal: move `label`/`secondary`/`title` to an optional View `annotationKinds` object and keep `color`/`stamp` in the Theme; each property is optional.

**Roles (Theme `roles`, one set shared by every kind; absent role = absent element).**

| Role (semantic id) | Element | Properties |
| --- | --- | --- |
| `annotation-kind-label` (`annotationKindLabel`) | line 1 text | typography, `fill`, `contrastTreatment` |
| `annotation-kind-secondary` (`annotationKindSecondary`) | sub-line text | typography, `fill`, `contrastTreatment` |
| `annotation-kind-bar` (`annotationKindBar`) | title bar Rect behind the header | Rect paint (`fill`, `opacity`, pattern), `chipPadding`, `markCornerRadius` (reuse of the label-chip ratios) |
| `annotation-kind-accent` (`annotationKindAccent`) | accent edge Rect | Rect paint, new `edgeSize`, `edgeSide` |
| `annotation-kind-stamp` (`annotationKindStamp`, A584-2) | stamp glyph | glyph paint, new `stampSize`, `stampCorner` |

New role properties (admitted for their role only, in `scene/capabilities.py`): `edgeSize` (named length, px, > 0), `edgeSide` (`start|end|top|bottom`), `stampSize` (named ratio of the note text size, > 0), `stampCorner` (`start-top|end-top|start-bottom|end-bottom`). All are optional additions to `theme-v0.13` and `theme-v0.11` role properties and to the `annotationKinds` definition, in place, no version bump (Specification 56 section 3.2); the S0 gate result is recorded in each schema PR.

### 5.2 Header text (D3)

The header is line 1 plus an optional line 2:

- line 1 is the `title` template rendered with the closed placeholders `{label}`, `{secondary}` and `{subject}` (the anchored object's title) and `{{`/`}}` escapes; any other brace use is `E_THEME_ANNOTATION_KIND_TEMPLATE` at the Theme pointer (one code; no expressions, no conditionals);
- line 2 is `secondary` set in `annotation-kind-secondary`, unless the template uses `{secondary}` (then it is inline and there is no line 2);
- `{secondary}` in the template without a `secondary` is the same error code. Text is never ellipsised or wrapped (a header is short by construction); a header wider than the available width widens the box and the existing visible-overflow rule reports it, as for any wide note.

The grammar is a ten-line parser in a new pure module `presentation/annotation_kind_text.py`; it does not import `group_header_text.py` (that module is #586's file and its grammar has other placeholders). Rejected: structured parts (more schema, no extra reach), a View-side template (D2).

### 5.3 Colour (D4)

`color` takes the grammar of a Theme colour binding (a closed Scheme intent or `category:<slot>`) and resolves in `resolve_theme` to a concrete colour, like a binding; an unknown slot is `E_SCHEME_INTENT_UNKNOWN`. Content normalisation emits `SurfaceContentInput.annotation_kind_paints` (annotation id, colour) from the kind and the resolved Theme; Scene paint completion replaces only the visible fill of the bar, accent and stamp primitives whose `source_ref` is that annotation id (opacity, order and geometry stay the role's). A kind with no `color` keeps the role's own Scheme fill. Rejected: per-kind roles (roles are a closed registry, kinds an open vocabulary) and a View-declared scale (the Theme owns the vocabulary here, so a scale would add a second declaration of the same domain).

### 5.4 Geometry and composition (D5), all in Layout

Layout composes each kind-dressed annotation in a local frame, then (A584-3) transforms it rigidly. In inline/block terms (start is the inline start; the codebase is left-to-right throughout):

- **Header block** height is the sum of the header line heights (each its role's `fontSize x lineHeight`) plus, when the bar role is declared, twice the bar block padding (`chipPadding x label font size / 2`); its inline size is the widest header line plus twice the bar inline padding (`chipPadding x label font size`). Without a bar the lines simply stack above the body, no padding.
- **Content box** = accent insets (`edgeSize` on `edgeSide`) around the header block stacked on the body text box; its inline size is the maximum of the body width and the header inline size. For an image outline the #465 content insets surround this content box exactly as they surround the text box today. The result is the box `annotation_size` that the #466 search, rail and collision already use, so no search code changes.
- **Elements.** The accent Rect lies on its edge over the full side; the bar Rect fills the top of the remaining inline extent; header text baselines sit inside the bar padding; body text moves down by the header block. Paint order: the box 400, accent and bar 400 (emitted after the box), all text 401 and above, so the bar is the ground the header text lies on.
- **Outline admission.** The bar and the accent are straight strips at the box edge, so they are admitted only on a `rectangle` outline; the header text (and A584-2's stamp) are admitted on every outline. A kind with a bar or accent role on an annotation whose box role is a balloon or image container is `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE` (role, outline, annotation id): a declaration conflict, not content, and never silently dropped.
- **No kind header when the role is absent.** A Theme with `annotationKinds` but without `annotation-kind-label` shows no header text and no bar (the bar is the ground of the header), though an accent edge may still be declared.

### 5.5 Contrast (D6)

- The two text roles are `STATE_TEXT`-classified (`contrastTreatment` required, as `annotation-note-text`) and **optional** like `period-label`. The Theme-resolution check `_state_text_contrast` compares a role's fill with the Scheme `surface`, which is the wrong ground for text on a per-kind bar; for these two roles it is replaced by `_annotation_kind_text_contrast`: the fill against each declared kind's bar colour when the bar role exists (the bar's role fill when a kind has no `color`), else against the note box's fill. Failure is `E_SCHEME_ANNOTATION_KIND_CONTRAST` at the role pointer, detail `<kind>:<ratio>`.
- The Scene gate (`contrast_policy`) takes the ground of these two roles from the same-source completed Rects (the bar, else the note box) by the existing sample-point rule, so a per-kind colour is the ground that is measured, per annotation. This is the rule `_note_box_ground` already applies to note prose, generalised from one hard-coded role pair to a small role-to-host-roles table.
- The bar, the accent and the stamp are `DECORATION`-classified (floor 1.10 against their ground), so their paint cannot vanish into the note box. That registers them in the corpus decoration witness, which is why each slice commits an evidence slide.
- A kind colour changes only fill, so no existing finding changes for a Theme that declares no kind.

### 5.6 Stamp (D7, A584-2)

`annotationKinds.<kind>.stamp` is a `set:name` catalogue glyph reference, resolved through the pinned Context into Layout-completed outline parts exactly as a gate glyph is (`closure` collects it as a read catalogue entry; an unknown name is `E_THEME_ASSET_REFERENCE` at the Theme pointer). Role `annotation-kind-stamp` gives the paint (each part paints from the role colour or its declared fixed colour; the kind `color` replaces the fill channel), `stampSize` (a ratio of the note text size, the square the glyph is fitted contain/centred into) and `stampCorner`. **Reserved column:** the stamp takes an inline column `stampSize + gap` at the start or end of the content box over its full block extent; its corner picks the top or bottom of that column. The bar, the accent and the text shrink to the remaining inline extent, so the stamp never overlaps text (the column below a top stamp is empty note paint; a Title Card hazard corner sets `stampSize` to the bar height and reads as the bar's end cap). A stamp is admitted on every outline. `E_LAYOUT_ANNOTATION_STAMP_SIZE` when the size is not positive. Rejected: an overlay with no reserved space (it can cover text), a glyph per purpose (kind is the key).

### 5.7 Tilt declaration and geometry (D8, D9, A584-3)

**Where (D8, judgement call).** The Theme owns it, as a property of the `annotationContainer` token: `tiltDegrees`, a non-empty array of numbers, each in `[-15, 15]`, admitted only with `outline: rectangle` (a balloon tail and an image's slice tiles do not rotate by this rule; combining is `E_THEME_TOKEN_TYPE` at the property pointer). The issue lists View; the angle is how a target dresses a note ("tilt ... are Theme treatments", #718 README), the same View may be shown under a Theme with and a Theme without it, and the schema file in question stays the Theme's. Reversal: move the array to an optional View `annotations[].tilt` or `annotationPresentation` and read it in the same Layout function.

**Rule (deterministic).** The annotation at position `i` of `SurfaceContentInput.annotations` (the View's declared order, independent of placement success) takes `tiltDegrees[i mod len]`. `[0]` or no property is none; `[a]` is a fixed angle; `[a, -a]` is alternation; a longer list is a declared cycle. There is no random source, hash, clock or iteration order, so two renders are equal; the "seed" is the declared list and the position. Angles are clockwise in degrees (the SVG and Layout sense), rounded to two decimals; the bound 15 keeps the rotated bounds within a fixed factor of the unrotated ones. One cycle covers the issue's none, fixed and alternation without three modes.

**Geometry.** Layout measures the unrotated local frame as in 5.4, then computes the axis-aligned bounds of that frame rotated about its centre. The #466 search, the rail and the collision use those rotated bounds (`annotation_size` becomes the rotated bounding size, so no search code changes), and the obstacle index registers the rotated bounds. After a position is chosen, every element of the frame (box, bar, accent, stamp, text baseline and bounds) is rotated about the box centre: Rects become closed `Symbol` paths, each text keeps its measured lines with its baseline origin rotated and its bounds replaced by the rotated bounding box. A leader targets the nearest side midpoint of the **rotated** box, not of the bounding box, so it ends on the paper. A note with label visuals (`visuals` on `annotation-text:<id>`) cannot rotate (an Icon has no rotation): `E_LAYOUT_ANNOTATION_TILT_VISUAL`, never a silently unrotated icon.

**Scene and adapters.** `TextLayout` gains orientation `tilt` with a finite `rotation_degrees` (non-zero, within the bound); `scene-v0.7` `textLayout.orientation` and `rotationDegrees` widen in place and `scene_document` selects v0.7 when a tilt is present, as for a glow (Scene v0.6 is not edited). SVG rotates the text about its baseline start (already generic in angle) and draws the rotated box as a `Symbol` path; TikZ does the same (`rotate=` on a `base west` node); Typst rejects the `Symbol` box with `E_VISUAL_CAPABILITY_UNSUPPORTED` as it does for a balloon today, so no unverified Typst pivot is shipped. The contrast gate samples the centre of the rotated text's bounds, which lies inside the rotated box, so the existing ground rule and the same-source host rule judge the rotated text; a synthetic test proves a too-close fill is an error on rotated text.

### 5.8 Intended incompatibilities and failure behaviour

None for any existing document: every property is optional and its absence is today's output. New codes are raised only for a document that uses the new property.

| Condition | Code | Raised at |
| --- | --- | --- |
| Template grammar, unknown placeholder, `{secondary}` without `secondary`, empty `label` | `E_THEME_ANNOTATION_KIND_TEMPLATE` | Theme closure |
| Unknown `color` intent or slot | `E_SCHEME_INTENT_UNKNOWN` (existing) | Theme resolution |
| Label text fails its floor against a kind colour (or the note fill) | `E_SCHEME_ANNOTATION_KIND_CONTRAST` | Theme resolution |
| Bar or accent role with a balloon or image box | `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE` | Layout |
| Non-positive `edgeSize` or `stampSize`, unknown side or corner | `E_THEME_TOKEN_TYPE` (existing) | Theme tokens |
| Unknown stamp glyph | `E_THEME_ASSET_REFERENCE` (existing) | Closure |
| `tiltDegrees` outside the bound, empty, or on a non-rectangle outline | `E_THEME_TOKEN_TYPE` (existing) | Theme tokens |
| Label visuals on a tilted note | `E_LAYOUT_ANNOTATION_TILT_VISUAL` | Layout |
| A rendered header, bar or note below its gate floor | `E_SCENE_STATE_TEXT_CONTRAST`, `E_SCENE_DECORATION_CONTRAST` (existing) | Scene gate |

## 6. Architecture review

- **View selects, Theme paints, Layout places.** The kind is a Project fact carried through the View's existing `projectAnnotation` link; the View gains no property. Theme owns the vocabulary and appearance; Layout reads Theme strings and geometry only and completes every rectangle, path and text origin; Scene carries completed primitives and the kind colour as paint; adapters serialise.
- **No second mechanism.** The colour binding grammar is the Theme's; the header text reuses text placement; the stamp reuses the gate glyph path; the tilt reuses the existing `Symbol` path and text-rotation pivot; the contrast host rule generalises the note-prose rule.
- **Specification 56 section 3.2.** Theme additions are optional, in place in the two live theme schemas (`theme-v0.13`, transitioning `theme-v0.11`, exactly as #492 and #587), plus one optional Scene v0.7 widening in slice 3 selected by content; every PR runs `python -m tools.schema_equivalence --base-rev origin/main` and records the result, with an expected-delta entry only if the gate asks. `theme-v0.14` derived Themes replace whole `values`/`roles` entries and do not carry `colorScales` either; `annotationKinds` shares that limit.
- **Byte identity.** A Theme without `annotationKinds`, a role or `tiltDegrees`, and a Project without a kind, produce every committed Scene and SVG unchanged. Regenerating the public slides locally is evidence of no change only, not a quality bar; the behaviour is proven on synthetic fixtures and rendered images.
- **Contrast.** New text is `STATE_TEXT`, judged on its real ground at Theme resolution and in the Scene gate; new fills are `DECORATION`. A tilted text is gated like any other.
- **Cross-agent files.** No View schema, `group_header_text.py`, MCP, diagnostic-detail or container-artwork file is touched. The shared edits are the two Theme schemas, the expected-delta file, `scene-v0.7` (slice 3), the example manifest and public-slide count tests (one slide per slice, rebased last), and the specifications.
- **Rejected options.** Kind by purpose; a View `kind`; per-kind roles; a View scale for the kind colour; a stamp overlay without reserved space; three tilt modes; a bar on balloon or image outlines; shipping an unverified Typst tilt; absorbing #848.
- **Owner-level judgement calls** (options, choice, why and reversal on the issue): D1 kind source, D2 Theme `annotationKinds`, D3 template grammar and the secondary line, D5 reserved stamp column and outline admission, D8 tilt in the Theme as one cycle.

## 7. Implementation plan

Each code PR is `Refs #584`, leaves every committed example byte-identical for a document that does not use the new property, runs the S0 gate when it touches a schema, regenerates nothing by hand (the derived sync does), carries an evidence slide through new YAML, and names its mutation checks.

### A584-1: kind header, title bar, accent edge (one code PR)

- **Content.** `model/surface_content.py`: `AnnotationIntent.kind` and `SurfaceContentInput.annotation_kind_paints` (defaults empty); `review/v05_content.py:_annotation` reads the Project annotation's `kind` once beside `_annotation_text`; `render_review.py` resolves the paints from the resolved Theme.
- **Theme.** `schemas/theme-v0.13.schema.yaml` and `theme-v0.11.schema.yaml`: `annotationKinds` (`label`, `secondary`, `title`, `color`), role properties `edgeSize` and `edgeSide`; `schemas/schema-equivalence/expected-deltas-v0.1.yaml` if the gate asks; `scene/capabilities.py` registers the four roles and the two properties; `model/semantic_registry.py` the bindings (label and secondary `STATE_TEXT`, bar and accent `DECORATION`); `color_scheme.py`: resolve `color`, `_annotation_kind_text_contrast`, optional-role handling; `model/theme_tokens.py`: an `annotation_kind(kind)` accessor with validation; new pure `presentation/annotation_kind_text.py`.
- **Layout.** `layout/surface_annotations.py` (header block, insets, bar, accent, text offset, `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE`) with the frame composition in a new `layout/annotation_kind_frame.py` so `place_annotations` grows by a call, not a branch.
- **Scene.** `scene/v05_builder.py` emits the four placed elements and replaces their fill by the annotation's kind paint; `scene/contrast_policy.py` generalises the same-source host rule.
- **Specifications.** Specification 07 (Theme: `annotationKinds`, roles, properties), Specification 08 (Scene purposes), Specification 06 section 9 (the kind source), each a short normative paragraph.
- **Tests (synthetic, no `examples/`).** Unit: the template parser and every rejection; the Theme accessor and its validation; the frame geometry (header block, insets, box size) at each `edgeSide`. Integration through `tests/support/synthetic_review.py` with Project notes of two kinds: default (no `annotationKinds`) equal to the base render; header text per kind, with and without secondary and with `{subject}`; bar fill per kind; accent on each side; undeclared kind plain; bar on a balloon is the error; label contrast failure at Theme resolution and in the Scene gate (a kind colour too close to the label), and a legible one passing; the decoration findings for the bar and accent; determinism. **Mutation checks:** kind read from `purpose`, fill override on the wrong channel or id, header block omitted from the box size, accent inset on the wrong side, secondary line dropped, host rule widened to any Rect, the outline check removed.
- **Verification.** Focused tests, conformance, S0, the non-corpus suite once, regenerate public slides to prove no byte moved; a rendered image per variant read in full (bar plus sub-line, accent plus `{subject}`).
- **Evidence slide.** `examples/halcyon-1/`: a Theme derived by copying `wallboard.yaml` (Title Card-style roles and `annotationKinds` for `risk`/`note`) and a Context on the existing `02-programme-board` View and Project; a manifest entry; the public-slide count tests.

### A584-2: stamp (one code PR)

- **Theme.** `annotationKinds.<kind>.stamp`, role `annotation-kind-stamp` with `stampSize`, `stampCorner`; closure reads the glyph entry; registry binding `annotationKindStamp` (`DECORATION`).
- **Layout.** The reserved column and the glyph fitted into the stamp square in `annotation_kind_frame.py`; `E_LAYOUT_ANNOTATION_STAMP_SIZE`.
- **Scene.** Emit the glyph parts as the gate glyph does; kind paint replaces the fill channel.
- **Tests.** Stamp per kind and per corner at each side; the reserved column excludes the text (no overlap with text bounds); an unknown glyph is `E_THEME_ASSET_REFERENCE`; no-stamp byte identity; the stamp on a balloon and on an image box; the decoration finding. Mutations: corner mapped to the wrong side, column not reserved, wrong kind's glyph, fit not contained, kind fill ignored.
- **Evidence.** The same slide gains `seal-risk`/`seal-note` or `hazard-tab` stamps (extending A584-1's new files only).

### A584-3: tilt (one code PR)

- **Theme.** `annotationContainer.tiltDegrees` in both theme schemas; `theme_tokens.annotation_container` validation.
- **Layout.** `layout/annotation_tilt.py` (pure: angle for a position, rotated bounds, rotation of a rectangle to path commands, of a text placement, of a port); `surface_annotations.py` uses rotated bounds for the search and obstacles, the rotated side midpoint for the leader, and raises `E_LAYOUT_ANNOTATION_TILT_VISUAL`.
- **Scene.** `scene/model.py` (`TextLayout` accepts `tilt`), `schemas/scene-v0.7.schema.yaml` (in place), `serialization.scene_document` (v0.7 when present), `v05_builder.py` (rotated box as `Symbol`, text layout), perceptibility/occlusion read rotated bounds.
- **Specifications.** Specification 07 (the property), Specification 08 (Scene text and rotated box).
- **Tests.** Unit: the angle rule (fixed, alternation, cycle, position independence from placement), rotation maths, rotated bounds. Integration: default byte identity; rotated notes placed by the search using their rotated bounds (no overlap with an obstacle the unrotated bounds would clear); rotated text carries the angle and a baseline pivot; the Scene validates against v0.7 and v0.6 is never written; a leader ends on the rotated box edge; two renders equal; a too-close fill is a contrast error on rotated text; label visuals rejected; tilt on a balloon rejected. Mutations: angle indexed by placement order, rotation sign flipped, rotated bounds replaced by the unrotated, leader port from the bounding box, text rotated about the wrong pivot, bound check removed.
- **Evidence.** A Marquee-style Theme (tilt cycle) on the same View, new YAML only, with image read for SVG and the PNG path.

### Acceptance review

After the last merged slice: one `docs/reviews/current/issue-584-annotation-kinds-acceptance-review-<date>.md` with `<!-- chrona:literal-acceptance/v1 -->` and a row per criterion of section 2 (met, or narrowed with a successor searched for duplicates first), `tools/check_issue_acceptance_reviews.py` run unpiped, the review merged, the exact-main three-OS run located on the review commit and cited, and #584 closed only when every row is met or narrowed with a successor and that run is green.

## 8. Progress and evidence

Not started (design published in this revision).
