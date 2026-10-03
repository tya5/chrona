# Issue #1050: viewer-fit mode per box role (`raw`, `text-follows-box`, `box-follows-text`) (work record)

Living record for [#1050](https://github.com/tya5/chrona/issues/1050) (TOP on the [#454](https://github.com/tya5/chrona/issues/454) board, read only; target B README): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1050 (options, choice, why, how to reverse).

**Public base:** `4d97eccd` on `main`. **Status:** design plan, design, architecture review and implementation plan published together in one docs PR before code. One code slice (I1050-1) implements it, section 7.

## 1. Published baseline

#1050 has a body and one later comment (the reviewer's second case, a framed container); the other comment is this work's claim. Its ask: *Layout measures every run with the Theme's font (Noto Sans); the SVG names it (`font-family="Noto Sans, sans-serif"`) but does not embed it (#362; the owner decided fonts are not embedded); a viewer without it draws a wider fallback and a box sized from the measurement no longer holds its text (README hero, note `window-note`: 286.1 px of text in a 307.9 px box, the run ends about 10 px past the box; `controller-z/annotation-artwork` (#848): '1. Board arrival gates first' runs over the scroll's inner frame line, 7 px of clearance). Add a Theme declaration on box roles that carry text, `viewerFit: raw | text-follows-box | box-follows-text` (default `raw`, today's output) and `textFollowsBox: {adjust: spacing | spacingAndGlyphs}` (default `spacing`).* Read on `4d97eccd` from [`v05_svg.py`](../../../src/chrona/presentation/renderers/v05_svg.py) (one `<text>` per Scene Text, one `<tspan x dy>` per extra line, `font-family`, `transform` for rotation and #585 compression, no `textLength` anywhere), [`v05_typeset.py`](../../../src/chrona/presentation/renderers/v05_typeset.py) (Typst and TikZ draw Rects and Text, not SVG), [`registry.py`](../../../src/chrona/presentation/renderers/registry.py) (PNG is resvg on the SVG with the packaged fonts, PDF is svglib on the SVG), [`text.py`](../../../src/chrona/presentation/layout/text.py) (`place_text` measures each line through the declared metric at the role's compression, `wrap_text`), [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py) (one `place_text` for the body, `place_kind_frame` for header lines, rotation for #584 tilt), [`scene/model.py`](../../../src/chrona/presentation/scene/model.py) (`TextLayout` carries `bounds` (widest line) and `lines`, not per-line widths), [`serialization.py`](../../../src/chrona/presentation/scene/serialization.py) (Scene v0.7 carries optional additions), [`capabilities.py`](../../../src/chrona/presentation/scene/capabilities.py) (the closed Theme role-property registry: a role that declares a property no consumer reads is rejected), [`render_review.py`](../../../src/chrona/usecases/render_review.py) (target-aware warnings are projected after the renderer is known, as `W_FONT_GLYPH_SUBSTITUTED` is), Specifications 07 and 08, the [#1051 record](issue-1051-note-inline-size-2026-10-03.md) (box-role declarations live in the Theme; `fill` composes), #585 (compression is a measured `ScaledMetric` plus a `matrix(s 0 0 1 ...)` transform, resvg-verified), #497 (legend ellipsis: a layout-time fit, a different mechanism), #1049 (per-side border, in flight as PR #1081) and the README image `examples/halcyon-1/generated/21-target-b.svg` (the note text lines carry no `textLength`).

**Measured here, not inferred** (scratch SVG in headless Google Chrome on macOS, where `Noto Sans` is not installed as a family so the fallback is used, and resvg 0.48.1 with only the packaged fonts):

1. `textLength` with `lengthAdjust` on a `<text>` and on each `<tspan>` pins every run's advance in Chrome and in resvg, both adjust values, also under `transform="matrix(0.8 0 0 1 ...)"` (the value is in the text's own, pre-transform, frame, so it must be the measured width divided by the compression) and with `letter-spacing`. Under `<img>` nothing runs, so this is static and applies.
2. `<g filter>` with `feFlood` merged under `SourceGraphic` over region `x=0 y=0 width=1 height=1` paints a background that ends where the rendered text ends in Chrome (Courier New fallback grew the box, the packaged-face box is the text plus the trailing spaces) and in resvg. `xml:space="preserve"` keeps trailing spaces in both.
3. Raw text in the Courier fallback overflows the 300 px box by about 55 px (images read).

Unverified at design time: Firefox, Safari, GitHub's image proxy, PowerPoint/Keynote imports, svglib (PDF). svglib is not asked to honour either mode (D4); everything else is reported honestly in section 8.

## 2. Literal acceptance (copied from the issue, plus the assignment)

From the issue body, "Acceptance (synthetic fixtures; checked on the emitted SVG against the published Scene)":

1. `raw`: the output is byte-identical to today's.
2. `text-follows-box`, for single-line, wrapped multi-line, kind-header and table-cell fixtures: (a) every `<text>` of the box carries `textLength` equal to that Text primitive's measured inline size in the Scene (per line for wrapped text), within the serialiser's rounding; (b) `lengthAdjust` matches the declaration.
3. `box-follows-text`: (a) the box has no static background rect; (b) its text group references a filter whose region is `x=0 y=0 width=1 height=1` on the object bounding box; (c) the group contains the invisible start/top/bottom extent rect; (d) every line ends with the end-inset spacing.
4. Every rejected combination (non-rectangle, radius > 0, end/top/bottom border, vertical text if unsupported) fails schema validation with a pointer to the offending declaration.
5. A renderer fallback to `raw` emits a warning that names the box role.
6. `examples/halcyon-1` target B declares `text-follows-box` for the note box; regenerated, its SVG carries `textLength` on all note text.

From "Proposal" and the comment: renderer-neutral mode recorded on the Scene box primitive; fixed-font renderers (PNG, PDF) equal `raw`; vertical writing verified or rejected; a framed (artwork) container and a plain rectangle are both fixtures; the owner's criterion that every label box in the hand-drawn targets can be reproduced under at least one non-raw mode (survey in the issue; honest state in 5.9).

Assignment constraints: (a) general rules and knobs, corpus output is evidence and not an oracle; (b) defaults leave today's output byte-identical; determinism across operating systems; contrast gates unaffected; baseline profile, Typst and TikZ stated honestly; (c) synthetic tests with no `examples/` input, a way to test without a second font, rendered images read at normal size with the packaged font, mutation-checked, and an honest list of what cannot be verified in real viewers; (d) an evidence slide on Controller Z through YAML, not the reviewer's `examples/halcyon-1/*target-b*` YAML (not edited; the reviewer's PR #1061 adopts the knob, so row 6 is narrowed with a successor, 5.9); (e) other agents own routing (#1060), annotation box border (#1049), table and legend text roles (#1062): their files are avoided and shared schema and Spec diffs stay minimal.

## 3. Dependencies and neighbours

- Composes with, does not absorb: #1051 (`inlineSize: fill` fixes the box width; `text-follows-box` uses each line's own measured width, which fill leaves alone; `box-follows-text` has a view-time width and is therefore rejected with `fill`), #1049 (merged, PR #1081: `annotationContainer.border` per side; a start border is an ordinary static rect, an end, top or bottom border is rejected with `box-follows-text`), #584 (kind frame, tilt), #848 (artwork container), #585 (compression: `textLength` is divided by the scale), #362 (no embedding, unchanged), #497 (layout-time fitting stays out of scope).
- Files owned by this change: a new `layout/viewer_fit.py`, `scene/viewer_fit.py` (fallback diagnostics) and tests; small appended edits in `theme_tokens.py`, `capabilities.py`, `surface_quality.py` (two fields), `surface_annotations.py` (a few lines at the existing text and shape calls), `scene/model.py`, `scene/serialization.py`, `scene/v05_builder.py`, `v05_svg.py`, `registry.py`, `render_review.py`, the live schemas, Specifications 07 and 08. #1049's PR #1081 (merged) edited several of the same shared files; every edit here is appended or local to a call site, on top of it.
- Out of scope, recorded as successors (5.9): chip, legend, table-cell, bar-label and title-plate roles (their text is outside the annotation pipeline; #1062 owns the table and legend text roles), vertical group labels, layout-time fitting (wrap, shrink, condense, ellipsis: the owner is still deciding).

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A Theme makes a note box keep its text inside in any face: each text line is pinned to the width Layout measured. | #1050 |
| U2 | The same for a framed (artwork) note, a tilted note and a kind header. | comment |
| U3 | A Theme makes a plain text-hugging box that grows with the viewer's face. | #1050 |
| U4 | A render for a fixed-font target (PNG, PDF) is exactly the `raw` render; a target that cannot honour a mode says so. | #1050 |
| U5 | A Theme that declares nothing renders byte-identically. | #1050 |
| U6 | An impossible combination fails at its declaration, not silently. | #1050 |

Open decisions (decided in section 5, recorded on #1050): **D1** where the declaration lives; **D2** what `text-follows-box` pins; **D3** what `box-follows-text` is and requires; **D4** non-SVG targets and the warning; **D5** Scene representation and schema version; **D6** which roles are wired now; **D7** vertical text; **D8** how to test without a second font and what cannot be verified; **D9** how target B adopts it.

Responsibility boundary: the Theme declares the mode on the box role; Layout owns text measurement, so it stamps the per-line measured widths and, for `box-follows-text`, the end-inset spacing count; Scene carries those completed facts and the mode on the box and its text; the SVG adapter serialises them with no measurement; other adapters draw what they always drew. Data model: two optional Theme role properties; one optional `fit` member on `TextPlacement` and Scene `TextLayout`; one optional `viewerFit` on the box shape and Scene primitive. Migration: none, omission is today's output. Design review questions: can a declaration move a gate or a leader? Does the default stay byte-identical, also under tilt and compression? Is every rejected combination reachable by a test? Does PNG/PDF equal `raw` byte for byte at the SVG stage? Does Spec 56 section 3.2 hold?

Acceptance evidence: synthetic tests (section 7), mutation checks, conformance, the S0 gate, the corpus unchanged (byte identity), Controller Z images read in headless Chrome and resvg.

## 5. Design

### 5.1 The declaration (D1)

On the box's Theme role binding, beside the role's other box properties:

```yaml
roles:
  annotation-note-box:
    annotationContainer: note-container
    viewerFit: text-follows-box     # raw (default, absent) | text-follows-box | box-follows-text
    viewerFitAdjust: spacing        # spacing (default) | spacingAndGlyphs; only with text-follows-box
```

**Options.** (a) Role-binding properties on the box role (chosen). (b) Inside the `annotationContainer` value. (c) On each text role. (d) A View or Layout Profile property.

The issue asks for a declaration per *box role that carries text*: notes today, chips, legends, table cells and plates later. (b) would tie it to one container token and cannot serve the roles that have no container. (c) is per text role, but one run can be the text of many boxes, and the mode is a property of the box-and-text pair (box-follows-text changes the box). (d) puts a presentation choice outside the Theme (the issue calls it a Theme declaration; the viewer's font is a presentation fact, not View intent or slot size). (a) matches `tabPosition`, `backgroundTreatment` and `chipPadding`, which are box-role bindings, and the closed role-property registry (`capabilities.py`) already rejects a role that declares a property no consumer reads, which is exactly the "not silently degraded" rule for roles not yet wired (D6). Enums are inline, as `tabPosition` is; the issue's nested `textFollowsBox: {adjust}` becomes the flat `viewerFitAdjust`, because a role binding holds named tokens or inline enums and has no nested objects.

Reverse: remove the two properties; no data depends on them.

### 5.2 `text-follows-box` (D2)

Layout measures every line of every text run of the box with the metric `place_text` used (the role's family, weight, size, letter spacing, numeric spacing and compression) and stamps `line_inline_sizes` on the placement. Lines are measured as drawn, after `text-transform` (the measurement `wrap_text` uses). The SVG adapter writes `textLength` and `lengthAdjust` on the `<text>` (one line) or on each `<tspan>` (several lines), with `textLength = line size / horizontalScale` because the value lives in the pre-transform frame (the measured size already contains the compression). `lengthAdjust` is always written, as the declaration says (`spacing` by default).

- **Every line of the box.** The body lines and every kind-header line (`place_kind_frame`) of the note get it. The note index chip (`note-index:*`) is another box role and is not touched.
- **Ragged right edge kept.** A line is pinned to its own measured width, never the box's inner width, so a wrapped note is not justified.
- **Layout is unchanged.** Box, collision, leaders and placement use the same bounds; only the text's drawn advance is pinned. Tilt rotates the frame, and `textLength` acts in the text's own frame (verified in Chrome); #848's artwork, #1051's fill and #1049's borders are static and unaffected. In the packaged face the pinned width equals the natural width (no visible change except sub-pixel rounding); in a wider face the line is condensed to its measured width, in a narrower face it is spaced out to it. `spacing` changes only inter-glyph gaps (legible, can look loose or tight); `spacingAndGlyphs` also scales glyph outlines (exact width, distorted glyph shapes).

### 5.3 `box-follows-text` (D3)

The Scene still carries the completed static Rect (so Layout, collision, leaders, contrast and perceptibility keep judging the measured box). The SVG adapter, instead of a `<rect>`, writes at the box's paint position one group:

```
<g data-scene-id="annotation-box:ID" data-viewer-fit="box-follows-text" filter="url(#fit-HASH)">
  <rect data-scene-id="annotation-box:ID-extent" x=box.x y=box.y width=max(start inset, 1) height=box.h fill="none"/>
  <text ... xml:space="preserve">line<spaces></text>        (no textLength)
</g>
```

with one filter per distinct fill, `<filter id="fit-HASH" x="0" y="0" width="1" height="1"><feFlood flood-color flood-opacity result="bg"/><feMerge><feMergeNode in="bg"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`, whose region is the group's bounding box. The invisible rect pins the start, top and bottom to the measured box; the text's own advance plus the trailing spaces sets the end. Layout stamps `end_pad_spaces = round(end inset / measured space width)` (end inset = the right content inset, 0 without one); the adapter appends that many spaces to every line. The painted background may grow past the measured box (end edge and, with a taller face, block edges) at view time; Layout, collision and leaders keep the measured box, and this is stated in the specification.

**Rejected combinations**, each an error with a pointer, never a degrade:

| Combination | Where it fails | Pointer |
| --- | --- | --- |
| outline other than `rectangle` (balloon tail, image) | Theme token reader | `/body/roles/<role>/annotationContainer/outline` |
| `cornerRadius` > 0 | Theme token reader | `.../annotationContainer/cornerRadius` |
| `tiltDegrees`, `artwork` (a static drawing the box cannot follow) | Theme token reader | `.../annotationContainer/tiltDegrees`, `.../artwork` |
| `inlineSize: fill` (a view-time width cannot equal a fixed one, #1051) | Theme token reader | `.../annotationContainer/inlineSize` |
| `viewerFitAdjust` with any mode but `text-follows-box` | Theme token reader | `/body/roles/<role>/viewerFitAdjust` |
| `annotationContainer.border` with an `end`, `top` or `bottom` side (a `start` side is a separate static rect and is allowed, #1049) | Theme token reader | `.../annotationContainer/border/end` (or `top`, `bottom`) |
| a stroke, gradient, shadow, glow, pattern, image or wobble on the box itself | Scene paint completion | the box primitive and role |
| an annotation with a kind (kind bar, header and stamp are static chrome over the box) or a label visual | Layout | `/annotations/<i>` |

The reader rows are in the Theme token reader because the facts live in named tokens (`annotationContainer` is a value in `values:`), which JSON Schema cannot resolve, so the token reader raises `E_THEME_TOKEN_TYPE` at the offending declaration (the same layer and code the #1051 rules use); the enums and the property list themselves are in the live schemas.

### 5.4 Non-SVG targets and the warning (D4)

- **SVG:** both modes are written.
- **PNG (resvg) and PDF (svglib), which draw the packaged font:** the SVG stage is produced with the viewer fit switched off (`render_v05_svg(surface, viewer_fit=False)`), so the SVG fed to the rasteriser is byte-identical to the `raw` one. Reasons: the font is fixed, so there is nothing to absorb; filter and `textLength` support differ across rasterisers (svglib ignores filters, which would erase a box-follows-text background); and a fixed output must not depend on a rasteriser's bounding-box computation (determinism across operating systems). No warning: this is raw by identity, not a failed request.
- **Typst and TikZ:** draw the static Rect and the lines as before (raw). Neither has a verified way to pin a run's advance or to size a box from a rendered run, so a non-raw role is reported: `W_VIEWER_FIT_NOT_HONOURED:<box role>:<target>` (one per role and target, with the declared mode in the payload), projected in `render_review` after the renderer is known, next to `W_FONT_GLYPH_SUBSTITUTED`. Honest, as #585 states for Typst/TikZ: nothing is claimed about their output beyond "drawn as raw".
- **A third-party consumer of the SVG that ignores `textLength` or filters** (some PowerPoint or Keynote imports, svglib if fed this SVG directly) sees `raw` for text-follows-box. For box-follows-text a consumer that ignores filters drops the background (the group has no static rect); that is the cost of the mode, stated in the specification and the reason `text-follows-box` is the recommended mode and the default for target B. The Scene is unaffected.

### 5.5 Scene, schema and compatibility (D5)

`TextPlacement.fit` and Scene `TextLayout.fit` are an optional `TextFit(mode, adjust, line_inline_sizes, box_id, end_pad_spaces)`; `ShapePlacement.viewer_fit` and `ScenePrimitive.viewer_fit` are `raw` or the mode (box shapes only). The primitive carries the mode, as the issue asks. Scene JSON writes `viewerFit` on the box and `textLayout.fit` on the text only when non-raw, and `scene_document` writes a document that carries any as `chrona/scene/v0.7` (as #584 tilt and #585 scale already do); Scene v0.6 is not edited. Validation lives in the model constructors (text-follows-box has one positive width per line; box-follows-text has a box id, a non-negative spacing count and no widths) and in the SVG adapter (a box-follows-text box and its text refer to each other; anything else is `E_PRESENTATION_PRIMITIVE_INVALID`).

Schema: `viewerFit` (enum) and `viewerFitAdjust` (enum) are optional additions in place to the role binding of both live Theme schemas (v0.11 and v0.13), and `viewerFit` and `textLayout.fit` to `scene-v0.7`, as Specification 56 section 3.2 requires: they preserve behaviour when absent, so no version bump; a schema `default` annotation does not set a value (the token reader supplies `raw`). The role-property registry gains the two names for the four annotation box roles. The S0 gate `python -m tools.schema_equivalence --base-rev origin/main` runs in the code PR; its expected-delta entries name this change's own pointers, aged entries are retired with `--prune-stale`, and the result is recorded in the PR.

### 5.6 Layout wiring (stamp, no new placement rule)

A pure module `layout/viewer_fit.py` (`measure_fit(placement, mode, adjust, font_metrics)`, `end_pad_spaces`) returns a copy of a `TextPlacement` with its `fit`. `surface_annotations.py` calls it at the three existing sites for a role with a non-raw mode: after `place_text` of the body, over the kind-frame text, and it stamps the box shape's `viewer_fit` by index (before the tilt rotation, which keeps the field through `replace`). With `raw` (the default) none of the lines is reached; the default path is not entered.

### 5.7 Contrast, determinism, identity (D8 partly)

Contrast and perceptibility judge the Scene: the box Rect, its fill and bounds, and the Text and its paint are unchanged in every mode (`box-follows-text` flood colour is the box fill, written once), so no gate moves. All numbers come from Layout's declared-metric measurement and Python's number formatting, as today; SVG filters and `textLength` are evaluated only by a viewer, and PNG/PDF do not use them (5.4), so no output of this repository depends on a rasteriser's font engine. Font identity (#362, #1050 owner decision: not embedded) is unchanged: the SVG still names the family and does not embed it.

### 5.8 Vertical text (D7)

`textLength` acts on a text's inline axis in its own frame; the repository draws rotated and vertical text through a rotation transform (rotated runs, #584 tilt; group-label vertical segments are rotated runs), so it composes. No vertical text is a box-role text today (only the group-label role is vertical, #585, and it has no box), so nothing is wired and nothing is rejected: a `viewerFit` on a role without a consumer is `E_THEME_ROLE_PROPERTY_UNSUPPORTED` by the registry. Verified here: a quarter-turn run with `textLength` in Chrome (section 8). Vertical group tags remain successor work (5.9).

### 5.9 Roles wired now, target B, successors (D6, D9)

Wired now: the four annotation box roles (`annotation-callout-box`, `-highlight-box`, `-note-box`, `-arrow-box`), which is where the README overflow and the reviewer's framed case are. Chip, legend, table cell, bar label and title plate are other pipelines (text placed by surface table/legend/lane code, partly owned by #1062); wiring them is one `fit` call at each site plus a registry entry. Per the survey in the issue they are covered by `text-follows-box`. The owner's criterion ("every label box in the hand-drawn targets reproducible under at least one non-raw mode") is therefore *not* claimed here: this work covers the annotation boxes and states the rest as successors, filed per family after a duplicate search (acceptance row). Target B adopts the knob with one line in the reviewer's `note-container` role binding (`viewerFit: text-follows-box`); this work edits neither it nor any `examples/halcyon-1/*target-b*` file, so row 6 is narrowed with a successor (the reviewer's adoption, in #987's line of work), exactly as #1051 row 5 was.

### 5.10 Failure behaviour and extension points

Wrong value or conflict: `E_THEME_TOKEN_TYPE` (5.3); a role with no consumer: the registry's existing diagnostic; a Scene that violates 5.5: `E_PRESENTATION_PRIMITIVE_INVALID`; a box-follows-text paint conflict: a `SceneBuildError` naming the role; an unsupported target: the warning (5.4). Extension points: more box roles (a `fit` call and a registry entry), per-line `lengthAdjust` choices, a future embedded-font option (the owner may reverse the font decision; this layer stays valid and becomes a no-op in effect).

## 6. Architecture review

- **Layers.** Theme declares; Layout measures and stamps (it alone has font metrics); Scene carries completed facts; the SVG adapter serialises without measuring; PNG/PDF choose the raw serialisation; Typst/TikZ are untouched. No adapter re-measures, no Layout rule reads a viewer.
- **One measurement.** The width written is the one `place_text`/`wrap_text` measure; nothing is re-derived in the adapter except the division by the compression.
- **No second path, no hidden degrade.** The default path is not entered; every rejected combination fails at a declaration; the unsupported-target case warns by name.
- **Static box stays the authority.** For `box-follows-text` the Scene box is the measured, collision-checked one; the view-time growth is bounded by what a viewer draws and documented. A leader attaches to the measured edge, which can lie inside a grown background; the specification says so.
- **Gates.** No colour, floor or class changes. The group's flood is the box fill; no new paint exists in the Scene.
- **Adjacent designs.** #1051 (fill rejected with box-follows-text), #1049 (borders), #584 and #848 (static chrome the box cannot follow, rejected with `box-follows-text`; `text-follows-box` composes), #585 (compression divisor), #362 (unchanged), #497 and layout-time fitting (out of scope), #1062 and #1060 (files avoided). Spec 56 section 3.2 applies and is met.
- **Corpus evidence is not an oracle.** No corpus datum is edited; target B and the README image are read as evidence against the approved intent.
- **Compatibility.** A Theme that declares the property changes (its purpose); one that does not, does not. A Theme that declares `box-follows-text` on a box the rule forbids is rejected at load.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **I1050-1** | new `layout/viewer_fit.py`, `scene/viewer_fit.py`; `surface_quality.py` (`TextFit`, two fields); `surface_annotations.py` (three call sites); `theme_tokens.py` (`ViewerFitToken`, reader); `capabilities.py` (registry); `scene/model.py`, `serialization.py`, `v05_builder.py` (carry, validate, paint check); `v05_svg.py` (text attributes, group, filter, `viewer_fit` switch); `registry.py` (PNG/PDF raw); `render_review.py`, `diagnostic_messages.py` (warning); `schemas/theme-v0.11`, `theme-v0.13`, `scene-v0.7`; expected deltas; Specifications 07 and 08 | rows 1 to 5: single-line, wrapped multi-line (fill rail), kind header, framed artwork container, tilt, compression; `raw` byte identity; box-follows-text structure; every rejected combination with its pointer; PNG/PDF SVG stage equals raw; Typst/TikZ warning; Scene round trip and schema validation | the diagnostics inventory and ledgers (bot-regenerated) | one code PR |
| **Evidence** | none (scratch Controller Z YAML) | Controller Z slide through YAML: raw, text-follows-box, box-follows-text, framed artwork, with the font swapped to a wide and a narrow face in headless Chrome; the packaged-face PNG at normal size; images read | none | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1050-...` | literal rows, successors searched for duplicates | none | one docs PR, then the exact-main three-OS run |

**Synthetic fallback-font test (no second font).** Chrome's fallback is a viewer fact the test suite cannot create, so the rule is checked at the Scene/SVG boundary: a hand-built `SceneSurface` whose text claims a measured width smaller than any real face would give (the "metrics-bypassing wider fallback") must yield `textLength` equal to the claimed width, and the same Scene with `raw` must yield no `textLength`; box-follows-text is checked for the exact filter, extent rect and trailing spaces. The browser behaviour of those attributes is the measured evidence of section 1 and the evidence slide, not a pytest.

**Mutation checks (I1050-1).** `textLength` omitted; `lengthAdjust` ignored (fixed `spacing`); width taken from the box's inner width or from the Scene bounds instead of the line; compression divisor dropped; kind-header lines not stamped; a stamped width from the unpainted text; the default path entered without the property; box-follows-text keeps the static rect; the filter region altered; the extent rect dropped; trailing spaces dropped; the paint, kind, visual, fill, radius, outline, tilt or artwork rejection removed (one mutation each); PNG/PDF SVG not switched to raw; the warning dropped or not naming the role. Each must fail at least one test.

**Order and risk.** If implementation shows a rule beyond section 5 is needed (for instance Chrome or resvg treating a zero-size extent rect differently from the assumed one, or a trailing-space count off by a glyph), the slice stops and the cause is recorded here before code resumes.

## 8. Progress and evidence

Design published (this record). Code, evidence and acceptance follow section 7.
