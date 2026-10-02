# Issue #584: annotation kinds, title bar, accent edge, stamp and a deterministic tilt (work record)

Living record for [#584](https://github.com/tya5/chrona/issues/584): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `99a52a83` on `main`. **Status:** design plan, design, architecture review and implementation plan are published together in this record (PR #931). Code slices A584-1 (kind header: title bar, accent edge; PR #937), A584-2 (stamp; PR #944) and A584-3 (tilt; implemented, section 8) follow, each default-output-unchanged.

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
| `annotation-kind-accent` (`annotationKindAccent`) | accent edge Rect | Rect paint, new `edge` |
| `annotation-kind-stamp` (`annotationKindStamp`, A584-2) | stamp glyph | glyph paint, new `stampPlacement` |

New role properties (admitted for their role only, in `scene/capabilities.py`), each naming a structured token as `annotationContainer` does: `edge` (token type `edge`, `{side: start|end|top|bottom, size}` with `size` a px length > 0) and, in A584-2, `stampPlacement` (token type `stampPlacement`, `{corner: start-top|end-top|start-bottom|end-bottom, size}` with `size` a ratio of the note text size > 0). Side and size are validated together, so a role needs one property rather than two. All are optional additions to `theme-v0.13` and `theme-v0.11` (the role property, the token type and its value shape) and to the `annotationKinds` definition, in place, no version bump (Specification 56 section 3.2); the S0 gate result is recorded in each schema PR.

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
- **Content box** = accent insets (the `edge` token's `size` on its `side`) around the header block stacked on the body text box; its inline size is the maximum of the body width and the header inline size. For an image outline the #465 content insets surround this content box exactly as they surround the text box today. The result is the box `annotation_size` that the #466 search, rail and collision already use, so no search code changes.
- **Elements.** The accent Rect lies on its edge over the full side; the bar Rect fills the top of the remaining inline extent; header text baselines sit inside the bar padding; body text moves down by the header block. Paint order: the box 400, accent and bar 400 (emitted after the box), all text 401 and above, so the bar is the ground the header text lies on.
- **Outline admission.** The bar and the accent are straight strips at the box edge, so they are admitted only on a `rectangle` outline; the header text (and A584-2's stamp) are admitted on every outline. A kind with a bar or accent role on an annotation whose box role is a balloon or image container is `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE` (role, outline, annotation id): a declaration conflict, not content, and never silently dropped.
- **No kind header when the role is absent.** A Theme with `annotationKinds` but without `annotation-kind-label` shows no header text and no bar (the bar is the ground of the header), though an accent edge may still be declared.

### 5.5 Contrast (D6)

- The two text roles are `STATE_TEXT`-classified (`contrastTreatment` required, as `annotation-note-text`) and **optional** like `period-label`. The Theme-resolution check `_state_text_contrast` compares a role's fill with the Scheme `surface`, which is the wrong ground for text on a per-kind bar; for these two roles it is replaced by `_annotation_kind_text_contrast`: the fill against each declared kind's bar colour when the bar role exists (the bar's role fill when a kind has no `color`), else against the note box's fill. Failure is `E_SCHEME_ANNOTATION_KIND_CONTRAST` at the role pointer, detail `<kind>:<ratio>`.
- The Scene gate (`contrast_policy`) takes the ground of these two roles from the same-source completed Rects (the bar, else the note box) by the existing sample-point rule, so a per-kind colour is the ground that is measured, per annotation. This is the rule `_note_box_ground` already applies to note prose, generalised from one hard-coded role pair to a small role-to-host-roles table.
- The bar, the accent and the stamp are `DECORATION`-classified (floor 1.10 against their ground), so their paint cannot vanish into the note box. That registers them in the corpus decoration witness, which is why each slice commits an evidence slide.
- A kind colour changes only fill, so no existing finding changes for a Theme that declares no kind.

### 5.6 Stamp (D7, A584-2)

`annotationKinds.<kind>.stamp` is a `set:name` catalogue glyph reference, resolved through the pinned Context into Layout-completed outline parts exactly as a gate glyph is (`closure` collects it as a read catalogue entry; an unknown name is `E_THEME_ASSET_REFERENCE` at the Theme pointer). Role `annotation-kind-stamp` gives the paint (each part paints from the role colour or its declared fixed colour; the kind `color` replaces the fill channel) and `stampPlacement` (`size`, a ratio of the note text size, the square the glyph is fitted contain/centred into, and `corner`). **Reserved column:** the stamp takes an inline column of the stamp `size` plus a gap at the start or end of the content box over its full block extent; its corner picks the top or bottom of that column. The bar, the accent and the text shrink to the remaining inline extent, so the stamp never overlaps text (the column below a top stamp is empty note paint; a Title Card hazard corner sets the stamp `size` to the bar height and reads as the bar's end cap). A stamp is admitted on every outline. A non-positive size or an unknown corner is `E_THEME_TOKEN_TYPE`. Rejected: an overlay with no reserved space (it can cover text), a glyph per purpose (kind is the key).

### 5.7 Tilt declaration and geometry (D8, D9, A584-3)

**Where (D8, judgement call).** The Theme owns it, as a property of the `annotationContainer` token: `tiltDegrees`, a non-empty array of numbers, each in `[-15, 15]`, admitted only with `outline: rectangle` (a balloon tail and an image's slice tiles do not rotate by this rule; combining is `E_THEME_TOKEN_TYPE` at the property pointer). The issue lists View; the angle is how a target dresses a note ("tilt ... are Theme treatments", #718 README), the same View may be shown under a Theme with and a Theme without it, and the schema file in question stays the Theme's. Reversal: move the array to an optional View `annotations[].tilt` or `annotationPresentation` and read it in the same Layout function.

**Rule (deterministic).** The annotation at position `i` of `SurfaceContentInput.annotations` (the View's declared order, independent of placement success) takes `tiltDegrees[i mod len]`. `[0]` or no property is none; `[a]` is a fixed angle; `[a, -a]` is alternation; a longer list is a declared cycle. There is no random source, hash, clock or iteration order, so two renders are equal; the "seed" is the declared list and the position. Angles are clockwise in degrees (the SVG and Layout sense), rounded to two decimals; the bound 15 keeps the rotated bounds within a fixed factor of the unrotated ones. One cycle covers the issue's none, fixed and alternation without three modes.

**Geometry.** Layout measures the unrotated local frame as in 5.4, then computes the axis-aligned bounds of that frame rotated about its centre. The #466 search, the rail and the collision use those rotated bounds (`annotation_size` becomes the rotated bounding size, so no search code changes), and the obstacle index registers the rotated bounds. After a position is chosen, every element of the frame (box, bar, accent, stamp, text baseline and bounds) is rotated about the box centre: Rects become closed `Symbol` paths, each text keeps its measured lines with its baseline origin rotated and its bounds replaced by the rotated bounding box. A leader routes to the bounds' port as the search already does and then continues to the nearest point of the **rotated** box's edge (a short final segment), so it ends on the paper and the route search and port obstacle are unchanged. A note with label visuals (`visuals` on `annotation-text:<id>`) cannot rotate (an Icon has no rotation): `E_LAYOUT_ANNOTATION_TILT_VISUAL`, never a silently unrotated icon.

**Scene and adapters.** `TextLayout` gains orientation `tilt` with a finite `rotation_degrees` (non-zero, within the bound); `scene-v0.7` `textLayout.orientation` and `rotationDegrees` widen in place and `scene_document` selects v0.7 when a tilt is present, as for a glow (Scene v0.6 is not edited). SVG rotates the text about its baseline start (already generic in angle) and draws the rotated box as a `Symbol` path; TikZ does the same (`rotate=` on a `base west` node); Typst rejects the `Symbol` box with `E_VISUAL_CAPABILITY_UNSUPPORTED` as it does for a balloon today, so no unverified Typst pivot is shipped. The contrast gate samples the centre of the rotated text's bounds, which lies inside the rotated box, so the existing ground rule and the same-source host rule judge the rotated text; a synthetic test proves a too-close fill is an error on rotated text.

### 5.8 Intended incompatibilities and failure behaviour

None for any existing document: every property is optional and its absence is today's output. New codes are raised only for a document that uses the new property.

| Condition | Code | Raised at |
| --- | --- | --- |
| Template grammar, unknown placeholder, `{secondary}` without `secondary`, empty `label` | `E_THEME_ANNOTATION_KIND_TEMPLATE` | Theme closure |
| Unknown `color` intent or slot | `E_SCHEME_INTENT_UNKNOWN` (existing) | Theme resolution |
| Label text fails its floor against a kind colour (or the note fill) | `E_SCHEME_ANNOTATION_KIND_CONTRAST` | Theme resolution |
| Bar or accent role with a balloon or image box | `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE` | Layout |
| Non-positive `edge` or `stampPlacement` size, unknown side or corner | `E_THEME_TOKEN_TYPE` (existing) | Theme tokens |
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
- **Theme.** `schemas/theme-v0.13.schema.yaml` and `theme-v0.11.schema.yaml`: `annotationKinds` (`label`, `secondary`, `title`, `color`), role property `edge` and token type `edge`; `conformance/schema-equivalence/expected-deltas-v0.1.yaml` (the gate asked for entries); `scene/capabilities.py` registers the four roles and the property; `model/semantic_registry.py` the bindings (label and secondary `STATE_TEXT`, bar and accent `DECORATION`); `color_scheme.py`: resolve `color`, `_annotation_kind_text_contrast`, optional-role handling; `model/theme_tokens.py`: an `annotation_kind(kind)` accessor with validation; new pure `presentation/annotation_kind_text.py`.
- **Layout.** `layout/surface_annotations.py` (header block, insets, bar, accent, text offset, `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE`) with the frame composition in a new `layout/annotation_kind_frame.py` so `place_annotations` grows by a call, not a branch.
- **Scene.** `scene/v05_builder.py` emits the four placed elements and replaces their fill by the annotation's kind paint; `scene/contrast_policy.py` generalises the same-source host rule.
- **Specifications.** Specification 07 (Theme: `annotationKinds`, roles, properties), Specification 08 (Scene purposes), Specification 06 section 9 (the kind source), each a short normative paragraph.
- **Tests (synthetic, no `examples/`).** Unit: the template parser and every rejection; the Theme accessor and its validation; the frame geometry (header block, insets, box size) at each `edgeSide`. Integration through `tests/support/synthetic_review.py` with Project notes of two kinds: default (no `annotationKinds`) equal to the base render; header text per kind, with and without secondary and with `{subject}`; bar fill per kind; accent on each side; undeclared kind plain; bar on a balloon is the error; label contrast failure at Theme resolution and in the Scene gate (a kind colour too close to the label), and a legible one passing; the decoration findings for the bar and accent; determinism. **Mutation checks:** kind read from `purpose`, fill override on the wrong channel or id, header block omitted from the box size, accent inset on the wrong side, secondary line dropped, host rule widened to any Rect, the outline check removed.
- **Verification.** Focused tests, conformance, S0, the non-corpus suite once, regenerate public slides to prove no byte moved; a rendered image per variant read in full (bar plus sub-line, accent plus `{subject}`).
- **Evidence slide.** `examples/halcyon-1/`: a Theme derived by copying `wallboard.yaml` (Title Card-style roles and `annotationKinds` for `risk`/`note`) and a Context on the existing `02-programme-board` View and Project; a manifest entry; the public-slide count tests.

### A584-2: stamp (one code PR)

- **Theme.** `annotationKinds.<kind>.stamp`, role `annotation-kind-stamp` with `stampPlacement`; closure reads the glyph entry; registry binding `annotationKindStamp` (`DECORATION`).
- **Layout.** The reserved column and the glyph fitted into the stamp square in `annotation_kind_frame.py`; - **Scene.** Emit the glyph parts as the gate glyph does; kind paint replaces the fill channel.
- **Tests.** Stamp per kind and per corner at each side; the reserved column excludes the text (no overlap with text bounds); an unknown glyph is `E_THEME_ASSET_REFERENCE`; no-stamp byte identity; the stamp on a balloon and on an image box; the decoration finding. Mutations: corner mapped to the wrong side, column not reserved, wrong kind's glyph, fit not contained, kind fill ignored.
- **Evidence.** A second new slide, on Controller Z (new View, Theme and Context YAML on the existing Project): the HALCYON-1 Contexts are resolved through a local-store reader that cannot read a packaged catalogue pin, so the stamp slide pins `chrona-target-parts` where the other catalogue slides do. Title Card style: the dark texture Theme, an orange title bar and a hazard-tab stamp.

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

### A584-1 (implemented)

- **Behaviour change: none by default.** All 32 existing public slides regenerate byte-identical (`tools/regenerate_public_examples.py --check`), which is evidence only that no committed Theme declares `annotationKinds` or a kind role, not a quality bar. The S0 gate (`python -m tools.schema_equivalence --base-rev origin/main`) passes with four expected-delta entries per Theme schema (`annotationKinds`, the role property `edge`, the `edge` token type and its value shape).
- **Where.** `AnnotationIntent.kind` and `.subject` (`review/v05_content.py`, the Project annotation's `kind` through `projectAnnotation` and the anchored object's title), `SurfaceContentInput.annotation_kind_paints`; the pure grammar `presentation/annotation_kind_text.py`; the Theme accessors `ThemeTokenView.annotation_kind` and `annotation_kind_frame` (`model/theme_tokens.py`); `color_scheme.py` (`annotationKinds` validated and resolved, `_annotation_kind_text_contrast`); `layout/annotation_kind_frame.py` (measure then place, so `place_annotations` grows by two calls and a few offsets that are zero without a kind); `scene/v05_builder.py` (fill replacement by the annotation's kind colour); registry bindings and role contracts for `annotation-kind-label`, `-secondary`, `-bar`, `-accent`. Specification 06 section 9, 07 and 08 carry the rule.
- **Internal choices within the approved contract.** (1) The accent is one `edge` role property naming a token of the new type `edge` (`{side, size}`), instead of two separate role properties: it keeps `_property_owner` and the role schema to one name and validates side and size together. The stamp will follow with one `stampPlacement` token type, not the two properties of section 5.1. (2) The Scene contrast gate needed no new host rule: the generic ground rule (topmost prior opaque Rect or Symbol under the text's sample point) already resolves the header text on the bar, or on the note box when there is no bar, so the role-to-host table of section 5.5 was not built; the paired same-source rule stays specific to note prose. (3) The kind frame is read from the Theme only when an annotation's kind is declared, so a Theme or fixture that registers a role name without its geometry is not misread as dressed.
- **Tests (synthetic, no `examples/`).** `tests/unit/chrona/presentation/test_annotation_kind_text.py` (grammar and every rejection, composition), `test_annotation_kind_theme.py` (Theme resolution, kind colours, the contrast check on bar and on box, treatment, accessors, edge token), `tests/integration/test_annotation_kind_header.py` (25: default and undeclared kinds unchanged, own-text annotation has no kind, header text per kind with subject and secondary, absent roles, bar fill per kind and its geometry, header text inside the padding, box growth and body offset, a long header widens the box, paint order, the accent on each side, bar and accent together, balloon conflict, text-only header on a balloon, determinism, and the Scene gate on the bar, on a failing bar for one annotation only, on a vanishing accent and on the box when there is no bar). Fixture module `tests/support/annotation_kinds.py`.
- **Mutation checks.** See the list below; all 19 were killed. Header text from the purpose instead of the Project kind; subject as the object id; kind paint keyed by scene id, on the stroke channel, and also on the note box; header block missing from the box height; body text not moved below the header; accent start inset ignored by the body text; header width ignored by the box width; accent start and end swapped; bar spanning the accent strip; outline-conflict check removed; secondary line dropped; inline secondary still adding a line; header text painted under the bar; kind contrast check removed; kind text judged on the canvas surface again; an undeclared kind measured as dressed; kind colour intent unchecked.
- **Rendered check.** Synthetic slides read as images: bar variant (red `RISK · Task 0` with `WARNING` sub-line and blue `NOTE` bar over the light note box) and accent variant (a red or blue edge down the start side, header text stacked above the body). Evidence slide `halcyon-1/gallery-annotation-kinds` (Theme `wallboard-annotation-kinds`, derived by copy from `wallboard-image-notes` without its image container, the existing `15-gallery-image-notes` View and Project, no corpus datum edited) read as an image: three notes with kind-coloured bars (`Risk · Payload thermal-vacuum` in red, `Note · Ground station upgrade` and `Note · Launch window opens` in blue), a secondary line each and the accent edge.
- **Not verified by image:** Japanese kind labels (`警告`, `報告`), because the packaged Latin bundle has no kanji metrics in these Contexts; the label is plain text through the same path.

### A584-2 (implemented)

- **Behaviour change: none by default.** All 33 existing public slides regenerate byte-identical; a Theme without `annotationKinds.<kind>.stamp` or the stamp role is the header alone. The S0 gate passes with four more expected-delta entries per Theme schema (`stamp`, role property `stampPlacement`, the token type enum, the token value shape).
- **Where.** `AnnotationKindToken.stamp` and `AnnotationKindFrame.stamp_*` (`model/theme_tokens.py`); the resolved Theme keeps `stamp` (`color_scheme.py`); the Theme asset closure resolves each kind's stamp as a catalogue glyph (`model/closure.py`, `E_THEME_ASSET_REFERENCE` at `/body/annotationKinds/<kind>/stamp`); `layout/annotation_kind_frame.py` measures the stamp column and completes the glyph parts with the existing `symbol_parts`; `ShapePlacement.symbol_parts`; `scene/v05_builder.py` emits one Symbol per part and replaces the fill or stroke channel of each part by the kind colour; registry binding `annotationKindStamp` (`DECORATION`) and role contract. Specification 07 and 08 carry the rule.
- **Internal choices within the approved contract.** The stamp's box keeps the glyph's own aspect (a block size of `size` text sizes and an inline size from the viewport), so the 56 x 24 hazard tab and the 32 x 32 seals both fit without distortion; the gap between a stamp and the content is half a text size; a stamp taller than the note raises the note's block size to the stamp's (`max`), and the bar, header and body wrap in the remaining inline extent, so the declared `maxInlineEm` still bounds the whole note, column included. The Scene contrast gate (`contrast_policy._ground_under`) skips sibling parts of one stamp when it looks for the ground under a part: the parts of one glyph are one ink, so without this a fill part would be judged against an earlier fill part of the same colour (ratio 1.0, found when the first corpus run reported 12 errors for the hazard tab). A stamp glyph with stroked parts carries a required line cap and join, so it needs a visual profile that admits them (the rich SVG/PNG profiles), exactly as a catalogue gate glyph does; the baseline profile rejects it with `E_VISUAL_CAPABILITY_UNSUPPORTED` (tested). Shape errors of a `stampPlacement` token are the Theme schema's `E_THEME_SCHEMA` at a full render and `E_THEME_TOKEN_TYPE` from the accessor.
- **Tests (synthetic).** `tests/integration/test_annotation_kind_stamp.py` (24: no declaration or no role changes nothing, one Symbol per part in each kind's glyph and colour, each corner and the column, no overlap with any text, bar and body shrink for the column, a start stamp moves bar and body, a tall stamp sets the box height, the glyph's own aspect, a stamp inside an accent edge on each side, balloon admitted, unknown glyph and unpinned set, invalid placement, the baseline profile, determinism, the Scene gate on every part, the parts of one glyph not being each other's ground, and a vanishing stamp) and unit tests in `test_annotation_kind_theme.py`.
- **Mutation checks (17, all killed; one survivor of the first pass of 15, a bottom stamp ignoring the bottom accent, was killed by a new test).** Corner side swapped; column not reserved; stamp height missing from the box height; always the risk seal; drawn without its role; kind colour on the other channel; only the first part emitted; bottom and top stamp ignoring the accent inset; end stamp ignoring the accent inset; glyph aspect ignored; size ignoring the text size; closure not resolving the glyph; `stamp` dropped from the resolved Theme; corner check removed; non-positive size accepted; the parts of one stamp being each other's ground.
- **Rendered check.** Synthetic slide (red `RISK · Task 0` bar with a 危 seal at the end of the header, a blue `NOTE` bar with a 記 seal) and the new evidence slide `controller-z/annotation-kinds` read as images: an orange `Warning · EVB Arrival` bar with a `GATE REVIEW` line, the red accent edge, and the hazard-tab stamp at the end of the header in the kind colour, on the dark texture Theme; the bar and text end before the stamp column.

### A584-3 (implemented)

- **Behaviour change: none by default.** A Theme without `tiltDegrees`, an angle of 0 and a View without Project kinds render every existing public slide unchanged. The S0 gate passes with expected-delta entries for the Theme `annotationContainer` token value and the Scene v0.7 text layout; the older entries of the same nodes were repaired in the same change, because the gate fails a stale entry whose node has moved on (the precedent of #583 for `periods`).
- **Where.** `AnnotationContainerToken.tilt_degrees` (`model/theme_tokens.py`: rectangle only, non-empty, numbers within +-15, `E_THEME_TOKEN_TYPE` at the property); the pure `layout/annotation_tilt.py` (the cycle rule, clockwise rotation, rotated extent, polygons, rigid rotation of a shape and of a text run, the nearest boundary point); `layout/surface_annotations.py` (the angle by position, `annotation_size` replaced by the rotated extent for the search and the rail, the frame centred in the chosen bounds, rotation of the box, kind frame and body text at their creation points, the leader continued to the polygon edge, `E_LAYOUT_ANNOTATION_TILT_VISUAL`); `ShapePlacement` kind `Tilt`; `scene/model.py` (`TextLayout` accepts orientation `tilt`), `serialization.py` (v0.7 when a tilt is present), `schemas/scene-v0.7.schema.yaml` (in place), `v05_builder.py` (a `Tilt` shape is a `Symbol` polygon), `v05_svg.py` (the rotation printed with the shared number format, unchanged for the quarter turns), `layout/surface_quality.py` and `scene/perceptibility.py` (the stacked lines of one tilted note are not an intersection). Specification 07 and 08 carry the rule.
- **Internal choices within the approved contract.** A leader keeps routing to the bounds' port and then continues to the nearest point of the rotated box's edge (a short extra segment, at most a few pixels at 15 degrees), so the route search and the port obstacle are unchanged. The text-intersection exemption is by source and orientation rather than a polygon test: lines of one rigid note cannot overlap by construction, and different notes are separated by the bounds the search registered. An annotation without a Project kind, a balloon or an image outline never tilts. No tilt is applied to a note that has label visuals; it is an error, not a silently unrotated icon.
- **Tests (synthetic).** `tests/unit/chrona/presentation/layout/test_annotation_tilt_geometry.py` (28: the cycle and rounding, the rotation sense, extent, polygons, shapes, text, boundary point, the Scene text layout bounds), `tests/unit/chrona/presentation/test_annotation_tilt_theme.py` (17: the token, its bound and every invalid form, the schema rejecting balloon, image, out-of-range and empty), `tests/integration/test_annotation_tilt.py` (20: absent or zero changes nothing, a fixed angle, the cycle by the View's order, alternation, the box bounds equal the rotated extent of the untilted frame, notes apart and inside the plot, the body text and the kind frame rotated rigidly (baselines derived from the polygon axes), a stamp rotated with the note, a leader reaching the polygon edge, label visuals rejected, v0.7 for a tilted scene and v0.6 otherwise, determinism, TikZ and Typst, the contrast gate on rotated note text and on a rotated header, the perceptibility check, a mixed slide).
- **Mutation checks (24, all killed).** One angle for every note; anticlockwise rotation; the search seeing the unrotated size; the leader stopping at the bounds port; the baseline not rotated; the angle bound removed; tilt admitted on every outline; non-numbers accepted; label visuals allowed; the tilted scene written as v0.6; the text layout accepting any angle and a zero tilt; the scene check and the layout validation flagging the lines of one note; the frame not centred; kind shapes, kind text and body text not rotated; rotation about the corner; stamp parts not rotated; the angle not rounded and truncated; a zero angle still rotating; the polygon not closed.
- **Rendered check.** A synthetic slide (a bar note tilted +4 degrees and a second at -3, header, sub-line and body rotated with the box) and the new evidence slide `halcyon-1/gallery-annotation-tilt` (three notes at -2.5, +2 and -1.5 degrees on the programme board, a new Theme and View id over the 15-gallery sources, no corpus datum edited) read as images. The slide uses plot candidates with no connector: with a leader connector the Ground-station note found no routable free position on this board and fell back to the visible-overflow placement, with or without a tilt (the same fallback an untilted leader slide shows), so the leader behaviour is proved on synthetic fixtures instead.
- **Known limits.** Typst never draws a tilted note (it rejects the `Symbol` box, as for a balloon). The static Theme-resolution check of `annotation-note-text` compares the ink with the Scheme `surface`, so dark ink on a light note box over a dark canvas (the Marquee newsprint look) is rejected before the Scene gate can judge it against the note it lies on; that predates this work and is recorded in the acceptance review.
