# Issue #585: text treatments, horizontal compression and vertical writing mode (work record)

Living record for [#585](https://github.com/tya5/chrona/issues/585): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `7028bf2c` on `main`. **Status:** all slices are done: the record (PR #955), I585-1 horizontal compression (PR #959), the design correction for lane rows (PR #960) and I585-2 vertical writing (PR #966). The [acceptance review](../../reviews/current/issue-585-text-treatments-acceptance-review-2026-10-03.md) is published; successors for the narrowed and beyond-row gaps are [#981](https://github.com/tya5/chrona/issues/981), [#982](https://github.com/tya5/chrona/issues/982) and [#983](https://github.com/tya5/chrona/issues/983). The owner-level decisions are recorded as a comment on the issue.

## 1. Published baseline

Issue #585 has no comments before this work (body unchanged since filing). It is the P4-B text lane of #453's gap map (read only). Read on `7028bf2c`:

1. **A text role is five measured values and two finite switches.** `ThemeTokenView.text_treatment(role)` (`model/theme_tokens.py`) returns `TextTreatment`: family, weight, `fontSize`, `lineHeight`, `letterSpacing` (em), `textTransform`, `numericSpacing`. All are role properties naming Theme `values` tokens; the admitted set per role is `scene/capabilities.py:_TEXT_MEASUREMENT`, and `resolve_theme` rejects any other property with `E_THEME_ROLE_PROPERTY_UNSUPPORTED`.
2. **Measurement has one primitive.** `layout/text.py:measure_text_width` is the only caller of `FontMetrics.width`. Every Layout site selects a metric with `metric_for_role(theme_tokens, role, font_metrics)` (about 20 sites: table, axis, legend, annotations, member labels, lane labels, visuals, sources) and passes `letter_spacing=treatment.letter_spacing` beside it. Fit, wrap and ellipsis (`wrap_text`, `ellipsize_text`, table and column allocation, `text.measuredAverageAdvance`) all reduce to that call. Two places carry font attributes on their own records instead of a role: label visuals (`surface_quality` request item read by `surface_visuals`) and the dependency-network measured placement.
3. **The second measured text (#493) and secondary labels reuse the same call**, so a new horizontal factor that lives at that boundary reaches them without per-site edits.
4. **Scene text is one primitive per placement.** `TextPlacement` (`surface_quality.py`) becomes `TextLayout` (`scene/model.py`, `scene-v0.6`/`v0.7` `textLayout`) with `orientation` in `horizontal|rotate-cw|rotate-ccw|tilt` and `rotationDegrees`. `v05_svg` writes `transform="rotate(deg x y)"` about the baseline start; `v05_typeset` writes `#rotate(.., origin: top + left, reflow: false)` (Typst) and `rotate=` on a `base west` node (TikZ). #584 added `tilt` and selected `scene-v0.7` when a document carries it (`serialization.scene_document`).
5. **Group labels are one text per header row.** `layout/surface_groups.py:compose_group_presentation` places `group-header:<id>` text in the header row (`GroupPlacement.header_bounds`), reserved by `surface_base` only when the View's `grouping.presentation` is `header` (`group_header_size`). The label text is the Project entity title, replaced by the #583 template. The header row also counts in `surface_composer.timeline_content_block_requirement` and `surface_lanes` preflight. The table is `place_table_columns(bounds=table_bounds)` inside the table slot; grouped rows are indented by the hierarchy column's `table_cell_indent`. There is no row-spanning group column and no vertical text anywhere.
6. **The Scene gates are per primitive and bounds based.** `contrast_policy` judges each classified Text role against the ground under its sample point; `perceptibility` reports `E_SCENE_TEXT_SLOT_ESCAPE`, `E_SCENE_TEXT_OCCLUDED` and `E_SCENE_TEXT_INTERSECTION` from primitive bounds (tilted notes are exempted only inside one source). Rotated Text is already gated by its bounds (#584).
7. **Fonts.** The synthetic bundle (`tests/support/synthetic_review.py`, preset `executive-light`) uses the bundled Noto Sans faces, which carry **no CJK metrics**. The optional package `chrona-fonts-noto-cjk` (Noto Sans JP regular and bold, declared metrics v2) is the only CJK metric and font source; `resolve_draft_render(font_metrics_path=...)` accepts a descriptor that names it. CI installs the package (`AGENTS.md` setup); the committed `controller-z-ja` examples already render through it.
8. **Adapters, as they stand.** SVG is the base: PNG is `resvg_py` over the SVG (fonts passed explicitly), PDF is `svglib`/`reportlab` over the SVG. Typst and TikZ are source emitters (`chrona-typst/v0.1`, `chrona-tikz/v0.1`) that no test compiles. Measured on this base with the Python `typst` 0.15 wheel: the emitted `#place(left: .., top: ..)` is **rejected by that Typst** (`unexpected argument: left`), while the fragments `#rotate(.., origin: top + left, reflow: false)[..]` and `#scale(x: 60%, y: 100%, origin: left + top, reflow: false)[..]` compile when placed with `place(top + left, dx:, dy:)`. That pre-existing source-form gap is not part of this issue; it bounds what can honestly be claimed for Typst (section 5.4).
9. **Measured on this base with resvg (compression):** `transform="matrix(s 0 0 1 x(1-s) 0)"` on a 40 px Noto Sans Bold `Hello World` gives ink width 136 against 226 (0.60 exact, left edge fixed), and `rotate(90 x y) matrix(..)` scales along the rotated text axis (ink height 136), i.e. a scale applied in the text's own frame before the rotation. Separately, resvg lays out `writing-mode="tb"`/`vertical-rl` natively, CJK upright and Latin turned clockwise (read as an image); the design does not rely on it (section 5.5).

Inferred, not read: which target needs which treatment (section 4; from the READMEs `titlecard-target` and `yuya-target`, whose mock images were read: Title Card sets the title and month tier in heavy Mincho squeezed horizontally; Yuya has a narrow wooden tag per group, upright kanji stacked top to bottom with `・` between, spanning the group's rows beside a separate horizontal header row). Unverified until each slice: the rendered result (read as images), Typst and TikZ behaviour, PDF.

## 2. Literal acceptance (copied from the issue)

1. A Theme text role can declare `horizontalScale` (e.g. 0.6-1.0). Layout measures with it, and both adapters render identically. A synthetic measurement test shows the width scaling.
2. A Theme text role can declare `writingMode: vertical` for supported slots, starting with group labels spanning their rows. CJK and Latin rotation rules are stated in the spec and tested.
3. Evidence: Title Card title and Yuya group tags through YAML.

The issue's principle is part of the contract: general declarative knobs tested on synthetic fixtures; the design targets are reached afterwards by Theme/View YAML as evidence, not as a core pass condition.

## 3. Dependencies and neighbours

- #410 (text treatments), #493 (second measured text), #583 (group header text and tint), #584 (tilt, rotated Scene text) are closed and supply the machinery used. #718 packages the targets; this work adds knobs, not target presets.
- **Not touched:** #491 (axis cell corners: `axis.py`, `surface_axis.py` are not edited; their measurements receive compression through the shared metric boundary, not a per-site edit) and #588 (wobble stroke and affixes: `surface_member_labels.py` and `surface_content.py` are not edited for the same reason). #453 and #454 are read only.
- Shared files, kept minimal: `schemas/theme-v0.13.schema.yaml` and `theme-v0.11.schema.yaml` (one role property each, slice 1; one token type and its value shape, slice 2), `schemas/scene-v0.7.schema.yaml` (slice 1), `schemas/schema-equivalence/expected-deltas-v0.1.yaml`, Specification 07 and 08, `scene/capabilities.py`, the HALCYON example manifest and the public-slide count tests (one evidence slide per slice, rebased last).

## 4. Design plan

### Use cases

| Id | Use case | Targets |
| --- | --- | --- |
| U1 | A title (and month tier) is set in a heavy face scaled to 0.7 of its natural width; its measured width is the compressed width, so neighbours, wrapping and ellipsis see the narrower text | Title Card |
| U2 | A cramped column or label fits at 0.8 instead of ellipsising, and the fit decision is honest (the same width the painted text has) | any target |
| U3 | Each group has a narrow tag along the table's start edge: kanji upright top to bottom, Latin and digits turned sideways, spanning that group's rows | Yuya |
| U4 | Every existing View, Theme and Layout renders byte-identically | all |

### Slices, ordered by targets unlocked

1. **I585-1, horizontal compression (U1, U2).** A role property `horizontalScale`, measured at the metric boundary, carried through Scene and the adapters, with a floor and ceiling and a typed diagnostic. Unlocks Title Card and every compressed-label need; it is also the foundation of the "measured treatment" pattern slice 2 reuses.
2. **I585-2, vertical writing mode (U3).** A role property `writingMode` admitted only on the group-label role, Layout-completed per-segment Text, and a group tag column carved from the table's start. Unlocks Yuya. Larger and more structural, so second.
3. **Evidence (row 3).** Each slice adds one new evidence slide through new Theme/Context YAML on the existing HALCYON `02-programme-board` View and Project, editing no corpus datum. The Title Card heavy Mincho is not available (no Mincho face is packaged): the slide shows the treatment with Noto Sans JP Bold, and says so.

### Open decisions (closed in section 5)

- **D1 declaration of compression.** Role property naming a number token; a new token type; a View property; a font-stretch axis.
- **D2 range.** Floor and ceiling, whether expansion is admitted, where the typed diagnostic is raised.
- **D3 where measurement applies.** Per call site, or once at the metric boundary; what a scale does to letter spacing and to line height.
- **D4 Scene and adapters.** A new `textLayout` field and schema home; the transform composition with rotation; what Typst, TikZ, PDF do.
- **D5 declaration of vertical writing.** Role property and token type; which roles are "supported slots".
- **D6 vertical rules.** Direction, which characters are upright and which sideways, advance and alignment, overflow.
- **D7 vertical geometry.** Where the tag lives, what space it reserves, what happens to the header row, which surfaces are admitted.
- **D8 Scene and adapters for vertical.** One primitive per line or one per segment, new Scene vocabulary or the existing rotation.
- **D9 interaction.** `horizontalScale` with `writingMode`; compression with rotation/tilt.
- **D10 gates and evidence.**

### Responsibility and architecture review questions

- Does Layout alone own the measured width (the compressed one), with Scene carrying a completed factor and the adapters serialising it without deciding anything?
- Is there exactly one place a scale enters a measurement, so no site can forget it, and is a missed site detectable by a test?
- Is vertical writing completed by Layout into primitives the existing adapters already draw (no adapter shaping engine, no new Scene vocabulary)?
- Are both treatments optional and removable under Specification 56 section 3.2 and byte-identical when absent?
- Do the contrast and perceptibility gates cover every new Text primitive (per-segment vertical ink, compressed ink), on its real ground?
- Does anything collide with #491, #588 or the shared schemas?

### Acceptance evidence planned

Synthetic tests only (no `examples/` input; `tests/support/synthetic_review.py` plus the packaged bundle; the optional CJK provider for CJK cases): per treatment, the default (no declaration) output equal to the base render, each rule, each failure, an honesty sweep (every Text of a scaled role is exactly `s` times its unscaled width; a fit decision flips because the width changed), a rendered image read in full, a mutation check per rule. The S0 gate result in every schema PR. One evidence slide per slice through new YAML only. The literal acceptance review, `tools/check_issue_acceptance_reviews.py`, and the exact-main three-OS run.

### Order of publication

1. This record (one docs PR) with the owner-decision comment on #585. 2. I585-1 and I585-2 as separate code PRs, each `Refs #585`. 3. Acceptance review and the exact-main run.

## 5. Design

### 5.1 Horizontal compression: declaration and range (D1, D2)

**Declaration (D1).** A Theme text role MAY bind `horizontalScale` to a `number` token, exactly as it binds `letterSpacing`:

```yaml
values:
  title-squeeze: {type: number, value: 0.7}
roles:
  heading: {fontFamily: ..., fontSize: ..., lineHeight: ..., horizontalScale: title-squeeze, ...}
```

Absent means 1 (today's output). The property is admitted on every role that admits typography (`_TEXT_MEASUREMENT`); a role with the property and no text consumer is already `E_THEME_ROLE_PROPERTY_UNSUPPORTED`. Rejected: a new token type (a number is the whole value; the range is a rule, not a shape); a View property (how a face is set is appearance, like `letterSpacing`; the View selects roles); a `fontStretch` axis (no packaged face has a width axis, and metrics would not be measured from the face that paints).

**Range (D2, judgement call).** `0.5 <= horizontalScale <= 1`: compression only. Below the floor condensed glyphs stop being the same face (stems and counters collapse) and the treatment should be a different face; above 1 is a different treatment (extension) with different fit and legibility rules, and no target needs it. A value outside is `E_THEME_TEXT_SCALE_RANGE` at `/body/roles/<role>/horizontalScale` with the value as detail; a non-number token stays `E_THEME_TOKEN_TYPE`. It is raised at Theme resolution for every declared role (an unused bad role is still a bad Theme) and again by `text_treatment` for any direct token view. The floor and ceiling are two named constants beside `TextTreatment`; `1` is identical to absence (nothing is written to Scene). Reversal: change the constants (the schema has no range because the value is a token reference).

### 5.2 Measurement (D3)

`TextTreatment` gains `horizontal_scale: Decimal` (default 1). The scale enters **once, at the metric boundary**: `layout/text.py:metric_for_family`'s role selection returns, for a scale other than 1, a `ScaledMetric(base, scale)` whose `width()` is `scale x base.width(...)` and which delegates every other attribute (`content_identity`, `ensure_numeric_spacing`, ascent) to the base; for scale 1 it returns the base object itself, so default output is the same objects and the same numbers. Because every Layout site obtains its metric through `metric_for_role` and measures through `measure_text_width`, fit, wrap, ellipsis, table and axis column allocation, label and annotation boxes, and the measured sources all see the compressed width without a per-site edit. Re-wrapping an already scaled metric re-bases it (never scale twice). The two sites that bypass a role (label visuals and the dependency-network measured placement) carry `horizontal_scale` on their own records and wrap the family metric the same way.

What a scale means: it multiplies the **whole run width, letter spacing included** (that is what a transform of the painted run does), leaves the em height, line height and baseline untouched, and applies along the text's own inline axis (so quarter-turn and tilt text compress along its reading direction, before rotation). It is not applied to icons (`iconScale` is separate). Compression is a transform of the face, so stems are thinner than a true condensed design; this is stated, not hidden.

`place_text` records the factor on `TextPlacement.horizontal_scale`, so the bounds Layout computed (`width` is already the scaled width) and the factor Scene carries agree by construction.

### 5.3 Scene and adapters (D4)

- **Scene.** `TextLayout.horizontal_scale: float = 1.0`; serialised as `textLayout.horizontalScale` only when it is not 1. The property lands in `scene-v0.7` in place (Specification 56 section 3.2: optional, behaviour-preserving), with `exclusiveMinimum 0, maximum 1`-style bounds matching the Theme range; `scene_document` selects v0.7 when any Text carries it, as for a tilt or glow. `scene-v0.6` is not edited. `TextLayout.__post_init__` rejects a factor outside the range.
- **SVG and PNG (resvg), PDF.** The `<text>` carries `transform` = the existing rotation (if any) followed by `matrix(s 0 0 1 x(1-s) 0)` about the baseline start x, so the scale is applied in the text's own frame first. PNG is resvg over that SVG. PDF is svglib over the same SVG and is **not image-verified** here.
- **Typst.** `#scale(x: s%, y: 100%, origin: left + top, reflow: false)[..]` around the run, inside the existing `#rotate`. The fragment compiles on Typst 0.15 when placed with `place(top + left, ..)`, but the surrounding `#place(left:, top:)` emission is rejected by that Typst (section 1, item 8), so **no claim of a compiled Typst result is made**; the text is asserted and the gap is recorded.
- **TikZ.** Rejects a Text with a factor other than 1 as `E_VISUAL_CAPABILITY_UNSUPPORTED` (as Typst rejects a `Symbol`), because no LaTeX engine verifies an `xscale` pivot and an unverified pivot is not shipped (as #584 for Typst). A Theme without the property is unaffected.

"Both adapters render identically" is therefore claimed for the SVG/PNG route (image-verified) and, as source, Typst; not for TikZ (typed rejection) or PDF (unverified).

### 5.4 Vertical writing: declaration and rules (D5, D6)

**Declaration (D5).** A text role MAY bind `writingMode` to a token of the new type `writingMode` whose value is `horizontal` or `vertical`. Absent means horizontal. "Supported slots" is the role contract registry: `writingMode` is admitted **only** on the group-label role `groupHeader` (the typography role `compose_group_presentation` places). On any other role it is the existing `E_THEME_ROLE_PROPERTY_UNSUPPORTED`; the set grows by registering another role, with its own layout rule. `horizontal` is today's output.

**Rules (D6), fixed in Specification 07 and tested.** Vertical here is the CSS `vertical-rl`/`text-orientation: mixed` reading of a single column: the inline direction runs down the block axis, glyph by glyph, and the block direction is right to left (only one column exists in this slice). The label is split into segments by character class:

| Class | Characters | Set |
| --- | --- | --- |
| upright | Hiragana, Katakana (U+3041-30FF except U+30FC), CJK ideographs (U+3400-4DBF, 4E00-9FFF, F900-FAFF), Hangul syllables (U+AC00-D7AF), CJK and fullwidth punctuation and forms (U+3000-303F, U+FF01-FF60) other than the rotated set | one Text per character, upright, advance 1 em |
| sideways, by exception | the prolonged sound mark `ー` (U+30FC), wave dashes (U+301C, U+FF5E), dashes (U+2014, U+2015), the ellipsis (U+2026), brackets `「」『』（）［］｛｝【】〈〉《》〔〕` and ASCII brackets | not upright even where they lie in a CJK block: their vertical form is the horizontal glyph turned a quarter turn, so they join the surrounding sideways run |
| sideways | everything else: Latin, digits, ASCII punctuation, spaces, any other script | a maximal run is one Text turned a quarter turn clockwise (tops to the right), advance = the measured run width |

`text-transform` applies before segmentation. Letter spacing adds one `letterSpacing` after every segment but the last (and inside a sideways run, as in measurement). An upright character's advance is one em of its role size (the full-width cell) and its glyph is centred in the column by its measured width; a missing glyph is `E_FONT_GLYPH_UNAVAILABLE` like any measurement. A column's inline size (the line box) is `fontSize x lineHeight` of the role. A label longer than the extent it spans is cut at the segment boundary that fits and ends with the sideways ellipsis (`overflow: ellipsized`, source text kept), as table cells do. Not implemented, stated as limits: no OpenType `vert`/`vrt2` substitution (so the comma and full stop `、。` keep their horizontal-text cell position), no tate-chu-yoko (digit runs are sideways), no kerning or `palt`, one column only.

**Interaction (D9).** `horizontalScale` and `writingMode: vertical` on the same role is `E_THEME_TEXT_TREATMENT_CONFLICT` (a horizontal squeeze has no defined meaning along a vertical inline axis; the mapping is not guessed). A role with `writingMode: vertical` that is also bound where no vertical rule exists cannot occur (admission above).

### 5.5 Vertical geometry and Scene (D7, D8)

**Where.** With `grouping.presentation: header` and a `groupHeader` role that declares `writingMode: vertical`, on the table-timeline surface in either row mode (automatic rows or lanes), Layout reserves a **group tag column** at the start of the table slot. Its inline size is the role's line box; the table's columns, cells and hierarchy indent are laid out in the remaining `[table start + column, table end)`; group bands and row stripes keep their extents (the tag sits on them, its ink judged against the real ground). Each group's tag spans that group's **content rows** from the top of its first row to the bottom of its last, start-aligned, with half an em of clear space at each end so the tags of neighbouring groups stay apart (alignment is not a knob in this slice).

**The header row.** One label exists per group, so the vertical label **replaces** the horizontal header row: no header row is reserved (`group_header_size` is 0, in `surface_base`, `surface_composer.timeline_content_block_requirement` and the lane preflight through one shared predicate `vertical_group_tags(request)`), and `GroupPlacement.header_bounds` stays `None`. A horizontal title row beside a vertical tag (the Yuya mock shows both, with different text) is not part of this slice; it would need a second declared label and is a successor if wanted. With `presentation: band` there are no group labels and the property has no effect.

**Surfaces.** The corpus Views (and the packaged bundle) use lane rows, whose groups are placed by the same base geometry, so lane surfaces are admitted: the only lane-specific step is the preflight that counts header rows for the required block extent, which counts none when the label is vertical. (An earlier draft of this record rejected lanes with `E_LAYOUT_WRITING_MODE_UNSUPPORTED`; the discovery that every committed View is a lane View made that rule useless, so it is withdrawn and no such code exists.) The three header-row sites (`surface_base`, the lane preflight, and the render use case's timeline requirement) share one predicate.

**Scene (D8).** The existing vocabulary only. Layout completes every segment as its own `TextPlacement` (`group-tag:<group id>:<n>`, purpose `group-header`; a distinct prefix so it cannot meet the folded-point ids `group-header:<group>:<item>`): an upright character is orientation `horizontal`, a sideways segment orientation `rotate-cw` (90), both with `semanticId groupHeader` and the group's collision domain; bounds are the character's cell or the rotated run box, tiling the column without overlap. No Scene schema change, no adapter change: SVG, PNG, PDF-from-SVG, Typst and TikZ draw horizontal and quarter-turn Text today. Rejected: SVG `writing-mode` (measured: resvg does lay out `writing-mode: vertical-rl` with upright CJK and sideways Latin, but its extents come from the shaping engine and the font's vertical tables, which Layout cannot know before painting, so the tag column, the ellipsis and the gates would not rest on a measured width; svglib, Typst and TikZ have no matching route, so the adapters would disagree); a new `vertical` Scene orientation (an adapter shaping decision, against the layer rule); one primitive per label with newline-separated characters (couples advance to `lineHeight`). Cost: one primitive per upright character, bounded by a short tag.

### 5.6 Gates (D10)

- **Contrast.** A compressed Text keeps its role and its ground; every vertical segment is a Text with `semanticId groupHeader`, so the existing role-keyed gate judges each against the ground found under its sample point (the centre of its bounds, rotated or not). Synthetic tests prove a too-close fill is `E_SCENE_STATE_TEXT_CONTRAST`/the role's existing code on compressed text and on a vertical segment.
- **Perceptibility.** Slot escape, occlusion and intersection use the segment bounds; the tiling invariant (no overlap beyond the micro tolerance) is a test, as is `E_SCENE_TEXT_SLOT_ESCAPE` when a compressed or vertical text leaves its slot.
- **No new fill.** Neither treatment adds paint beyond Text, so no decoration floor or witness entry changes; the evidence slides still go through the contrast gate by being rendered.

### 5.7 Intended incompatibilities and failure behaviour

None for any existing document: both properties are optional and their absence is today's output. New codes are raised only by a document that uses the new property.

| Condition | Code | Raised at |
| --- | --- | --- |
| `horizontalScale` outside `[0.5, 1]` | `E_THEME_TEXT_SCALE_RANGE` | Theme resolution, `text_treatment` |
| `horizontalScale` or `writingMode` bound to a non-matching token | `E_THEME_TOKEN_TYPE` (existing) | Theme tokens |
| `writingMode` on a role that does not support it | `E_THEME_ROLE_PROPERTY_UNSUPPORTED` (existing) | Theme resolution |
| `writingMode` value not `horizontal`/`vertical` | `E_THEME_TOKEN_TYPE` (existing), schema | Theme schema, tokens |
| `horizontalScale` with `writingMode: vertical` on one role | `E_THEME_TEXT_TREATMENT_CONFLICT` | Theme resolution |
| compressed Text to TikZ | `E_VISUAL_CAPABILITY_UNSUPPORTED` (existing) | TikZ adapter |
| compressed or vertical text below its gate floor, or outside its slot | existing Scene gate codes | Scene gates |

## 6. Architecture review

- **View selects, Theme paints, Layout places.** The View gains no property. Theme declares how a role's text is set; Layout owns the measured (compressed) width, the vertical segmentation and the tag column; Scene carries a completed factor and ordinary completed Text; adapters serialise.
- **One entry point.** A scale enters measurement once, through the metric Layout already selects per role, so the ~20 measuring sites need no edit and none can forget it. The two sites that bypass a role are named, wrapped the same way, and covered by the honesty sweep. A new measuring site that bypasses `metric_for_role` would show up in that sweep.
- **No second mechanism for vertical.** It reuses `place_text`, `rotate-cw`, the group collision domain, the table slot and the existing ellipsis convention; the new code is segmentation plus a column reservation.
- **Specification 56 section 3.2.** Theme additions are optional, in place in the two live theme schemas (`theme-v0.13`, transitioning `theme-v0.11`, as #492, #587, #584); Scene adds one optional property to `scene-v0.7`, selected by content. Every PR runs `python -m tools.schema_equivalence --base-rev origin/main` and records the result; expected-delta entries are added only for deltas the gate reports as mine, and other agents' entries (including those the gate reports as unused or not applying on a newer base) are not edited.
- **Byte identity.** A Theme with neither property produces every committed Scene and SVG unchanged (identical objects through `metric_for_role`, no new Scene field). Regenerating the public slides is evidence of no change only, not a quality bar; behaviour is proven on synthetic fixtures and rendered images.
- **Honesty about what is verified.** Image-verified: SVG and PNG (resvg), Latin with the bundled Noto Sans, CJK with the optional Noto Sans JP package. Not verified: PDF, TikZ (rejected), Typst (fragments compile; the existing `place(left:)` emission does not on Typst 0.15). The synthetic bundle has no CJK metrics, so CJK cases need the optional provider and skip without it (a PR path twin uses Latin segments, so the rule is always tested).
- **Cross-agent files.** No axis-corner, wobble or affix file is edited. Shared edits are the two Theme schemas, `scene-v0.7`, the expected-delta file, `capabilities.py`, the specifications, the example manifest and public-slide count tests (one slide per slice, rebased last).
- **Rejected options.** New token type for the scale; View property; font-stretch; a scale above 1; per-site scaling; SVG `writing-mode`; a `vertical` Scene orientation; a second horizontal header row beside the tag; shipping an unverified TikZ `xscale`; treating the Typst `place` gap as part of this issue.
- **Owner-level judgement calls** (options, choice, why and reversal on the issue): D1 role property over a token type or View property, D2 range 0.5-1 compression only, D3 scale at the metric boundary, D4 TikZ rejects and Typst is source-only, D5 `groupHeader` only, D6 rule table and limits, D7 the vertical label replaces the header row, D9 conflict rejected.

## 7. Implementation plan

Each code PR is `Refs #585`, leaves every committed example byte-identical for a document that does not use the new property, runs the S0 gate when it touches a schema, regenerates nothing by hand (the derived sync does), carries an evidence slide through new YAML, and names its mutation checks.

### I585-1: horizontal compression (one code PR)

- **Theme.** `model/theme_tokens.py`: `TextTreatment.horizontal_scale`, floor/ceiling constants, `text_treatment` reads `optional_number(role, "horizontalScale")` and raises `E_THEME_TEXT_SCALE_RANGE`. `scene/capabilities.py`: add `horizontalScale` to `_TEXT_MEASUREMENT`. `presentation/color_scheme.py:resolve_theme`: range check for every declared role. `schemas/theme-v0.13.schema.yaml`, `theme-v0.11.schema.yaml`: one role property each. S0 gate result recorded; expected-delta entries only for what the gate asks.
- **Layout.** `layout/text.py`: `ScaledMetric`, role selection wraps it; `place_text` records `horizontal_scale`; `surface_quality.TextPlacement.horizontal_scale` and the label-visual request field, `dependency_network` copy.
- **Scene.** `scene/model.py` `TextLayout.horizontal_scale`, `serialization.py` field and v0.7 selection, `v05_builder.py` two construction sites, `schemas/scene-v0.7.schema.yaml` property, `scene/perceptibility.py` unchanged.
- **Adapters.** `renderers/v05_svg.py` transform composition; `renderers/v05_typeset.py` Typst `#scale`, TikZ typed rejection.
- **Specification.** 07 (property, range, diagnostic) and 08 (Scene field, adapter behaviour and limits).
- **Tests (synthetic, no `examples/`).** Unit: `ScaledMetric` and `place_text` widths (exactly `s` times unscaled, letter spacing included), range and conflict diagnostics, scene-document version selection. Integration (`tests/integration/test_horizontal_scale.py`): default byte identity against the base render; honesty sweep (every Text of a scaled role is `s` times its unscaled bounds; a table cell and an axis label that ellipsise at 1 fit in full at the scale; an annotation wraps to fewer lines); resvg PNG ink width ratio; contrast and slot-escape gates on compressed text; TikZ rejection; Typst source. Mutation checks: drop the metric wrap, wrap twice, ignore letter spacing, drop the SVG transform, drop the diagnostic.
- **Evidence.** One slide `gallery-text-compression` (new Theme, View and Context YAML over the 02-programme-board sources; `heading` and the axis month tier compressed, Noto Sans JP Bold as the heavy face; no corpus datum edited), rebased last.
- **Publication boundary.** One PR; after merge the derived sync commits the generated slide.

### I585-2: vertical writing mode (one code PR)

- **Theme.** `writingMode` token type and value shape in both theme schemas; `ThemeTokenView.writing_mode(role)`; `capabilities.py` registers `writingMode` on `groupHeader` only; `resolve_theme` conflict check.
- **Layout.** New pure module `layout/vertical_text.py` (classification, segmentation, advances, ellipsis, per-segment `TextPlacement`s); `surface_groups.py` places the tag segments; one shared predicate for the header-row sites (`surface_base.py`, the `surface_lanes.py` preflight, `usecases/render_review.py`); `surface_table.py` receives table bounds shifted by the tag column; `SurfaceBaseGeometry` carries the column size.
- **Scene and adapters.** None.
- **Specification.** 07 (property, supported slot, the rule table, limits, diagnostics) and 08 (tag column and per-segment text).
- **Tests.** Unit: classification table over each class boundary, segmentation, advances, ellipsis, the conflict diagnostic. Integration (`tests/integration/test_vertical_writing.py`): default byte identity; Latin-only twin on the bundled font (always runs); CJK with Noto Sans JP through the optional provider (skips without it); tiling without overlap, spanning of each group's rows, table shifted by exactly the column, header row not reserved, band presentation unaffected; contrast and escape gates on vertical segments; resvg image read. Mutation checks: classify a kana as sideways, swap the rotated set, drop the table shift, keep the header row, wrong advance, drop the end inset, drop the conflict diagnostic.
- **Evidence.** One slide `gallery-vertical-group-tags` (new Theme, View and Context YAML over the 02-programme-board sources, `grouping.presentation: header`, `#583` template for the tag text, Noto Sans JP), rebased last.
- **Publication boundary.** One PR; after merge the derived sync commits the generated slide.

### Acceptance review

After I585-2: one literal acceptance review (`docs/reviews/current/issue-585-text-treatments-acceptance-review-<date>.md`, marker `<!-- chrona:literal-acceptance/v1 -->`), the exact-main three-OS run on the commit that publishes it, and closing only if every row is met or narrowed with a searched successor.
