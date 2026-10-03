# Issue #1087: draw a rectangle container's `cornerRadius` and let a box border follow it (work record)

Living record for [#1087](https://github.com/tya5/chrona/issues/1087) (successor of #1049, TOP on the reviewer board; the target-B mock notes have radius 3): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1087.

**Public base:** `3990b5fb` on `main`. **Status:** design plan, design, architecture review and implementation plan published together in one docs PR before code; one code slice (I1087-1) implements it, section 7.

## 1. Published baseline

#1087 (body, no comment but this work's claim). Its ask: draw a rectangle `annotationContainer`'s `cornerRadius` (paper, artwork, tilt polygon); lift the #1049 refusal so a per-side border follows the rounded outline (CSS: inner radius = outer radius - width, mitre through the corner); fixtures for each side, two sides, tilt, artwork, `fill`; the lead adds: Typst and TikZ stated honestly, contrast grounds kept correct, viewer-fit (#1050), leaders, defaults byte-identical, and a corpus regeneration with grouped diff review if committed Themes declared an ignored radius. Read on `3990b5fb` from [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py), [`annotation_border.py`](../../../src/chrona/presentation/layout/annotation_border.py), [`annotation_tilt.py`](../../../src/chrona/presentation/layout/annotation_tilt.py), [`balloon_geometry.py`](../../../src/chrona/presentation/layout/balloon_geometry.py), [`theme_tokens.py`](../../../src/chrona/presentation/model/theme_tokens.py), the live Theme schemas, [`v05_builder.py`](../../../src/chrona/presentation/scene/v05_builder.py), [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py), [`v05_svg.py`](../../../src/chrona/presentation/renderers/v05_svg.py), [`v05_typeset.py`](../../../src/chrona/presentation/renderers/v05_typeset.py), the [#1049](issue-1049-annotation-box-border-2026-10-03.md) and [#1050](issue-1050-viewer-fit-2026-10-04.md) records and the mock (`docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png`, image read: notes with a small corner radius and a flush start bar):

1. A rectangle container's `cornerRadius` (em of the annotation text size) is validated and not drawn: the box is a `Rect` with no `corner_radius`. A balloon uses it as a chamfer. No committed Theme declares a rectangle radius above 0: every rectangle container in `examples/` (ten, including the #1049 slide) has `cornerRadius: 0`; the packaged presets and `tests/fixtures` declare none. So drawing the radius changes no committed slide (verified by the corpus check in the code slice); it changes only a Theme that declares one.
2. Scene `Rect` carries an optional `corner_radius` that SVG (`rx`), Typst (`radius`) and TikZ (`rounded corners`) already honour (chips, swatches); PNG is resvg on the SVG and PDF is svglib on the SVG. A tilted box is a closed polygon `Symbol` of the four rotated corners; `PathCommand` supports `move`, `line` and `quadratic`, which SVG, Typst and TikZ draw.
3. #1049's strips are `Rect`s or mitred polygons of the straight trapezoids; the reader and schema refuse `border` with a radius above 0.
4. Contrast: note text is judged against the note box only, sampled at the text centre by bounds; the decoration roles judge strips against the substrate. Neither understands a rounded corner, so the corner guarantee must come from Layout.
5. #1050 (merged) already refuses `box-follows-text` with `cornerRadius > 0` (its flood filter paints a rectangle); `text-follows-box` changes only text attributes.

Unverified at design time: the rendered result and how Typst and TikZ draw the quadratic corners (section 8 records what was read).

## 2. Literal acceptance (from the issue, plus the lead's message)

1. A rectangle with `cornerRadius > 0` renders rounded paper.
2. A bordered one has per-side strips following the outline.
3. Fixtures for each side, two sides, tilt, artwork and `fill`.
4. The schema and reader rule from #1049 (refuse `border` with a radius) are lifted.
5. (Lead) Typst and TikZ stated honestly; contrast grounds correct at the shrinking corners; composes with tilt, artwork, `fill`, viewer-fit, leaders; defaults byte-identical, corpus checked with images if anything changes; synthetic tests with no `examples/` input, mutation-checked; the decision on how borders follow the radius recorded.

Constraints: the reviewer's `examples/halcyon-1/*target-b*` YAML (PR #1061) and #454 are not touched; nothing else is retired (#1088 stays).

## 3. Dependencies and neighbours

Composes with, does not absorb: #1049 (strips), #848 (artwork), #1051 (`fill`: the chrome sum is unchanged), #1050 (refusal stays), #584 (tilt, kind frame). Files owned: `annotation_border.py` (arc geometry), a new `layout/rounded_outline.py` (pure), call sites in `surface_annotations.py`, `annotation_tilt.py` (one outline), `theme_tokens.py` (lift the radius refusal), the live Theme schemas, `v05_builder.py` (one argument), tests, Specifications 07 and 08. Avoided: #1060, #1061, #1088.

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A note box has a small corner radius (the mock's 3 px) and a flush kind start bar that follows the rounded corner. | mock, #1087 |
| U2 | Any side or sides of a rounded box carry borders of their own width and ink, following the outline with mitred corners. | #1087 |
| U3 | A tilted, artwork, filled or leader-attached rounded note behaves like a square one. | assignment |
| U4 | Text never sits outside the rounded paper, so the contrast ground under it is the paper. | lead |
| U5 | A Theme without a rectangle radius is byte-identical; a Theme with one now sees it drawn, and can restore the square look. | lead |

Open decisions (section 5, recorded on #1087): **D1** radius unit and clamp; **D2** paper and tilt; **D3** how borders follow it; **D4** text clearance; **D5** artwork; **D6** viewer-fit; **D7** leaders and contrast; **D8** default and knob. Boundary: Theme declares, Layout completes the outline and strips, Scene carries `Rect(corner_radius)` and polygon `Symbol`s, adapters serialize. No View, Project or Layout Profile change; one Theme rule lifted.

## 5. Design

### 5.1 Radius and paper (D1, D2)

The radius is `cornerRadius * annotation text size` (the em unit the property already has, and the balloon's), clamped to `min(width, height) / 2` of the paint box (the same clamp SVG applies, so Layout and the adapters agree). Zero draws exactly what is drawn today. A non-tilted rectangle box is the same `Rect` with `corner_radius` set. A tilted box is the closed path of the rounded rectangle, rotated with the frame: each corner is two quadratic segments of at most 45 degrees (the radial error of one quadratic over 90 degrees is 6 percent, over 45 degrees 0.3 percent; the same primitive the balloon and the SVG, Typst and TikZ adapters already carry). Rectangle outlines only: a balloon keeps its chamfer, an image keeps `cornerRadius: 0`.

### 5.2 Borders follow the outline (D3)

**Options.** (a) Full CSS: each side is the part of the ring between the outer rounded rectangle and the padding rounded rectangle, cut by the mitre lines. (b) Restrict a rounded box to a uniform or start-only border. (c) Draw the border as one stroked outline (cannot give per-side width or ink). **Chosen (a).** For outer radius `R` (clamped as above) and widths `wv` (the vertical side) and `wh` (the horizontal side) at a corner, the padding corner radii are `rx = max(R - wv, 0)` and `ry = max(R - wh, 0)` (an ellipse when the widths differ, a sharp corner when either is 0). The mitre is the line from the box corner to the padding-box corner `(wv, wh)`; it meets the outer arc at `t = R((wv + wh) - sqrt(2 wv wh)) / (wv^2 + wh^2)` along `(wv, wh)` and the padding arc at the smaller root of `s^2 A - 2 s B + 1 = 0` with `A = wv^2/rx^2 + wh^2/ry^2`, `B = wv/rx + wh/ry` (a sharp padding corner is its own cut point). A side's strip is: the outer outline from its first cut point to its second, the mitre to the padding outline, the padding outline back, the mitre back. Elliptical arcs are the circular arcs scaled, drawn as quadratics of at most 45 degrees. Width-0 sides emit nothing; a side whose corners are both square and unmitred is still a plain `Rect` (so a rounded box's strips are polygons only on the corners that curve: a start bar on a box with radius is a polygon, a start bar on a box with radius 0 is the `Rect` of #1049, unchanged). A side's extent along the box edge is still the full side (the strip's bounds are the box side), and its outer edge is the box edge on the straight run. Reverse (restrict): refuse `border` again with a radius.

### 5.3 Text clearance and contrast (D4, D7)

A rounded corner removes paper where a text line's corner could stand. Layout guarantees the text and the kind frame stand on paper: when `R > 0` the effective inset of each side is at least `R (1 - 1/sqrt 2)` (the clearance at which a point at that offset from both edges of a corner is on the arc). The floor enters the same four sums as the border and the content inset (text origin, kind content box, wrap, `fill` chrome, box size), so there is one rule, and it is zero for `R = 0`. Note text is then judged against the paper by its centre exactly as today (the sample is far from a corner); the strips are decorations over the note box and warn as before; no gate, class or code changes. Leaders end on an edge midpoint, which lies on the straight run because `R <= min(w, h) / 2`.

### 5.4 Composition (D5, D6)

- **Artwork (#848)** is painted unclipped over the rounded paper: it is its own outline (a scroll, a clipping), and clipping a decorative frame to a radius is a different feature; a Theme that wants a rounded paper under artwork gets it, with the artwork's ink on top.
- **Tilt** rotates the rounded outline and the strips with the frame; `fill` solves the same tilt (the chrome is unchanged by the radius except the clearance floor).
- **Viewer-fit (#1050):** `box-follows-text` stays refused with a radius (its flood filter paints a rectangle); `text-follows-box` composes (it changes only text).
- **Adapters (corrected at implementation).** SVG draws `rx` on the Rect and the quadratic path; PNG (resvg) and PDF (svglib) draw the SVG; TikZ draws `rounded corners` on the Rect and the Symbol outline (its quadratic mapping repeats the one control point as both cubic controls, which bulges a short arc by a few percent). Typst draws Rects and Text only and refuses any surface that carries a `Symbol` with `E_VISUAL_CAPABILITY_UNSUPPORTED`: that already covered a tilted box, a balloon and #1049's mitred strips (the #1049 text that said Typst drew them was wrong and is corrected in Specification 08 by this change), and now covers a rounded strip. A rounded paper without a border is a plain `Rect` with a radius, which both draw. Nothing was compiled with Typst or TikZ here; the checks are on the generated text.

### 5.5 Default, knob, schema (D8)

`cornerRadius: 0` (or the property's absence, which the schema requires) is today's output byte for byte; the committed corpus declares no rectangle radius above 0, so no slide changes (the corpus check proves it; no grouped diff is needed, and none can be unread). A Theme that declared a radius that was ignored will now see it drawn; the knob to restore the square look is `cornerRadius: 0`. The schema change is the removal of the `cornerRadius: const 0` consequence from #1049's border rule (an in-place relaxation of a rule added in the previous merge, Specification 56 section 3.2: no version bump, behaviour for inputs that were accepted is unchanged; the rejected input is now accepted); the token reader drops the same condition. The S0 gate runs with one L1 entry per live Theme schema.

### 5.6 Failure behaviour and extension points

A radius below 0 stays `E_THEME_TOKEN_TYPE` (the reader). A border width above half the box is geometry the strips clamp (the padding rectangle is empty) like CSS. Extension: per-corner radii; clipping artwork to the outline; the same outline for chips and legend boxes.

## 6. Architecture review

Theme declares, Layout completes (one new pure module and call sites), Scene and adapters unchanged except one forwarded argument; one strip geometry (`side_strip` and the mitre formula) remains the border's. No gate weakened; the clearance floor is a Layout rule with a test. Default byte-identical. Adjacent designs: #1049, #848, #1050, #1051, #584. Compatibility: a Theme with a rectangle radius above 0 changes by drawing it; no other Theme does.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **I1087-1** | new `layout/rounded_outline.py`; `annotation_border.py`; `surface_annotations.py`; `annotation_tilt.py`; `theme_tokens.py`; `scene/v05_builder.py`; both Theme schemas; expected deltas; Specifications 07 and 08 | rounded `Rect` paper; each side, two sides, four sides on a rounded box (strip bounds, mitre, outer edge on the box, inner follows the radius); tilt; artwork order; `fill`; leader; clearance floor; `box-follows-text` still refused; radius 0 byte-identical; the SVG and the Typst and TikZ outputs carry the radius | bot ledgers | one code PR |
| **Evidence** | a Controller Z slide through YAML (new `annotation-rounded`, or an extension of `annotation-border` only if no corpus datum changes) | images read | the slide (bot) | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1087-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks.** Radius not applied to the paper; not clamped; tilt polygon square; strip outer arc ignored (square strips); padding arc ignored; mitre cut wrong; elliptical radii swapped; clearance floor dropped; border refusal not lifted; box-follows-text accepted; default path entered with radius 0. Each must fail a test.

## 8. Progress and evidence

**Design** merged as PR #1103 (decisions recorded on #1087). **I1087-1 (Refs #1087).** `cornerRadius` of a rectangle `annotationContainer` is drawn: the paper is a `Rect` with `corner_radius` (clamped to half the shorter side), a tilted note the rotated rounded outline (two quadratic segments per corner), and `border` follows it (new pure `layout/rounded_outline.py`: outer and padding outlines, elliptical padding radii, the mitre cut points solved in closed form, one polygon `Symbol` of arcs per side); every inset is at least `R (1 - 1/sqrt 2)`; the token reader and both live Theme schemas admit `border` with a radius (S0 gate PASS, one L1 entry per schema; six aged #1050 entries retired with `--prune-stale`). Specifications 07 and 08 state the rule and correct the #1049 adapter sentence. Choices made while coding, inside the approved contract: a rounded strip's bounds are sampled from the arcs (exact for the unrotated and rotated outline); the leader of a tilted rounded note attaches to the sampled outline, not the four corners; TikZ and Typst were found to differ on Symbols (section 5.4, corrected).

Tests (synthetic, no `examples/`): `tests/integration/test_rounded_container.py` (rounded paper, clamp, default byte-identity and no-container case, each side, two sides with the mitre, four sides, clearance, `fill`, tilt, artwork order, leader, SVG, Typst and TikZ), `tests/unit/chrona/presentation/layout/test_rounded_outline.py` (the strips tile the ring between the outlines for six width and radius cases, sampled on a grid) and the token tests. 14 mutations (paper radius not applied, no clamp, clamp at the full side, square tilt outline, square strips, padding arc ignored, padding radii swapped, outer and inner mitre cuts wrong, clearance dropped, refusal restored, default drawing a radius, quadratic controls not rotated, one 90-degree quadratic per corner) were each killed, one after adding a test.

Evidence: every existing slide's Scene and SVG is byte-identical (`regenerate_public_examples.py --write` changes only the new slide; no committed Theme declares a rectangle radius above 0, so there is no grouped diff and no unread image). New Controller Z slide `annotation-rounded` (a note with radius 0.25 em, a 4 px kind start border and a 1 px bottom border; a callout with radius 0.6 em and a 3 px ink border on four sides), full slide and 3x crops read as images: the rounded paper, the start bar following the rounded left corners flush with the edge at full height, and the four mitred curved corners of the callout. Not verified: Typst and TikZ output was checked as generated text, not compiled; viewers other than resvg.
