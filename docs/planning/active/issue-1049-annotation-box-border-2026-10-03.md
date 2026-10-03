# Issue #1049: per-side box border on annotation containers (work record)

Living record for [#1049](https://github.com/tya5/chrona/issues/1049) (TOP on the [#454](https://github.com/tya5/chrona/issues/454) board, read only; target B notes rail): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1049 (options, choice, why, how to reverse).

**Public base:** `730bc5b9` on `main`. **Status:** design plan, design, architecture review and implementation plan published together in one docs PR before code. One code slice (I1049-1) implements it, section 7.

## 1. Published baseline

#1049 has a body and no comment other than this work's claim. Its ask: the annotation-kind accent is drawn 8.4 px inside the note box (short, no text gap); model it as a CSS-style per-side border on `annotationContainer` (`border.start|end|top|bottom` with a width and a paint, `kind` meaning the annotation kind colour); the border lies on the outer edge and spans the full side; the content inset is measured from the border's inner edge; a width-0 side emits nothing; `image` and `balloon` either support borders or the schema rejects `border` there; the existing `edge` accent becomes sugar for a start border or is migrated, with one layout path; target B then declares a 3 px start border. Out of scope: fitting text into a fixed box, dashed or double styles. Read on `730bc5b9` from:

1. [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py): the paint box is `bounds`; `content_top/right/bottom/left` are the container's content insets; the note text starts at `frame + content inset + kind accent inset`; the kind frame is placed in `frame - content insets` (so the accent sits inside the inset, which is #1049's defect); `measure_note` and #1051's `chrome` sum add the content insets to the box size.
2. [`annotation_kind_frame.py`](../../../src/chrona/presentation/layout/annotation_kind_frame.py): the accent is a Rect of the `edge` token's size on the content box's side; `annotation-kind-accent` role, purpose, `ContrastClass.DECORATION`; the kind colour replaces its fill in Scene (`_complete_primitive_paint`).
3. [`theme_tokens.py`](../../../src/chrona/presentation/model/theme_tokens.py): `AnnotationContainerToken` (outline, `cornerRadius`, `contentInsetEm`, `tiltDegrees`, `artwork`, `inlineSize`, `maxInlineEm`); `annotation_kind_frame()` declares the accent whenever the role `annotation-kind-accent` exists and requires its `edge`.
4. Rectangle `cornerRadius` is read and validated but **not drawn**: the rectangle box is a plain `Rect` with no corner radius (only a balloon uses it); no corpus rectangle container declares a radius above 0 (`examples/` read: five containers, all `cornerRadius: 0`, plus three balloons at 0.2 and one image).
5. Tilt (#584) rotates every frame element rigidly (`rotate_shape`: a Rect becomes a closed `Tilt` polygon); #848 artwork is warped over the whole paint box and painted right after the box; leaders attach to the outer bounds' edge midpoint; label visuals (icons) are placed from `bounds.x + kind body inset` and do not add the content inset today.
6. Contrast: a decoration is judged against its substrate and warns (`W_SCENE_DECORATION_CONTRAST`); note text is judged against the note box Rect only (`_note_box_ground`), so a border painted after the box never becomes a text ground.
7. The mock (`docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png`, image read): three notes in one rail column, a 3 px start accent flush with the left edge at full box height, text starting a clear gap after it, wrapped to two lines.
8. #1051 (merged, [record](issue-1051-note-inline-size-2026-10-03.md) 5.7) designed `chrome` so #1049 adds border widths; #584, #848, #889 (region frame, not involved) and the contrast gate (#884, #950, #980, #1013) are reused unchanged.

Unverified at design time: the rendered result (section 8 records it) and whether any corpus note has a label visual together with a content inset (it decides whether the icon-offset correction in 5.6 is byte-neutral for the corpus; checked in I1049-1).

## 2. Literal acceptance (copied from the issue, plus the assignment)

From the issue, "Acceptance (checked on the published Scene, synthetic fixtures)": for every annotation with a bordered side, on a fixture covering each side (`start`, `end`, `top`, `bottom`), two sides at once, `cornerRadius` 0 and > 0, and every `outline` that supports borders:

1. The border primitive's outer edge equals the box's outer edge on that side.
2. Its length equals the box's full length on that side.
3. Every text primitive of the note lies inside the box, inset from each bordered side by at least that side's border width plus the content inset.
4. Nothing is placed between the border and the box edge.
5. A side with width 0 emits no primitive.
6. For `outline: image` or `balloon`, if borders are not supported there, the schema rejects `border` for that outline; it is not silently ignored.
7. Then regenerate target B and confirm the notes rail matches the mock: flush accent, full height, text gap.

From the body: the border follows CSS (mitred corners, inset measured from the inner edge, outer size = content + inset + border, a rounded outline is followed when `cornerRadius > 0`); the `edge` accent becomes sugar or is migrated, one layout path.

Assignment constraints: (a) a general Theme declaration, per-side width and ink (role or colour), measured relative to the box; defaults leave today's output unchanged, with a knob if a default would change; (b) composes with tilt, artwork, `fill` (#1051), leaders; SVG and PNG adapters, Typst and TikZ stated; (c) synthetic tests with no `examples/` input, mutation-checked; (d) rendered images read through a Controller Z evidence slide, not the reviewer's `examples/halcyon-1/*target-b*` YAML (not edited; reviewer PR #1061 adopts the knob), so row 7 is narrowed with a successor; (e) contrast gates: a border is decoration (warning), text over the box stays blocking; (f) avoid the files of #1060, #1044, #1063, #1066.

## 3. Dependencies and neighbours

- Composes with, does not absorb: #1051 (the wrap bound is `outer - chrome`; the border widths join the one `chrome` sum, nothing else changes), #848 (artwork under the border), #584 (kind frame, tilt), #1050 (viewer fit: not designed here).
- Reused unchanged: the paint pipeline (a Theme role gives the fill; the kind colour override), the contrast registry classes, the S0 gate.
- Files owned by this change: new `layout/annotation_border.py` (pure geometry), call sites in `surface_annotations.py` and a one-line shared strip helper use in `annotation_kind_frame.py`, `theme_tokens.py` (token fields, accent presence), `semantic_registry.py` and `capabilities.py` (four border roles), `v05_builder.py` (one branch), both live Theme schemas, expected deltas, tests, Specifications 07 and 08.

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A note shows its kind colour as a bar flush with the start edge, full height, text clear of it. | #1049, mock |
| U2 | Any side (or several) of a note box carries a border of its own width and ink; a width-0 side draws nothing. | #1049 |
| U3 | The box grows by the border: wrap, `fill` (#1051), search and collision see the outer box. | #1049, #1051 |
| U4 | A tilted note, a note with artwork, and a leader behave as without a border. | assignment |
| U5 | A Theme that does not declare `border` renders byte-identically, and a Theme that declares the old `edge` accent renders as before. | assignment |
| U6 | Borders on a balloon, an image, or a rounded rectangle are refused, not ignored. | #1049 |

Open decisions (section 5, recorded on #1049): **D1** how the accent relates to the border (one path); **D2** the ink vocabulary; **D3** units and logical sides; **D4** corners (mitre) and primitives; **D5** which outlines and radii; **D6** composition (inset, wrap, `fill`, tilt, artwork, leaders, visuals, paint order); **D7** target B adoption and the knob.

Responsibility boundary: the Theme declares `border` next to the other box declarations; Layout owns the completed strips (geometry, mitre, rotation) and the box size; Scene carries completed Rect or polygon Symbol primitives with a role and a purpose; adapters serialize. Data model: one optional object on the `annotationContainer` value; four new Theme roles (ink); no View, Project or Layout Profile change; no Scene member. Migration: none (omission is today's output). Design review questions: does the default stay byte-identical? Is there one strip geometry for border and accent? Can a text line ever sit on the border? Does a gate weaken? Does 3.2 hold?

Acceptance evidence: synthetic tests (section 7), mutation checks, conformance and the corpus unchanged, a Controller Z image read, the S0 gate.

## 5. Design

### 5.1 The declaration (D1, D3)

On the `annotationContainer` token value, rectangle outlines:

```yaml
annotationContainer:
  outline: rectangle
  cornerRadius: 0
  contentInsetEm: {top: 0.7, right: 0.7, bottom: 0.7, left: 0.7}   # measured from inside the border
  border:
    start:  {width: 3, paint: kind}     # paint: kind | ink (default ink)
    top:    {width: 1, paint: ink}
```

Each of `start`, `end`, `top`, `bottom` is optional and is `{width, paint}`; `width` is a number >= 0 in surface units (px, as the `edge` token's `size`; not em, so a 3 px bar stays 3 px at any text size); an omitted side or width 0 draws nothing and takes no space. Sides are logical and resolve like the existing accent (`start` is the inline start, the left edge in the left-to-right surface). At least one side must be declared.

**Accent (D1). Options.** (a) Migrate the accent: `annotation-kind-accent`'s `edge` becomes `border.start` for every Theme (a default change: the corpus accents move to the box edge and gain full height). (b) Keep the `edge` accent as it is and add `border` beside it with no relation (two paths). (c) **Chosen:** the border is the one box-edge strip model, and `paint: kind` is how the kind accent is expressed in it; the legacy `edge` accent stays only as the strip of the *content box* (inside the inset) that today's Themes declare, drawn through the same strip function, so there is one strip geometry and one set of rules; a Theme migrates by deleting `edge` from the role and declaring `border.start {width, paint: kind}`. Default unchanged. This is the owner-approved model (accent as a start border) with the default flip left to the Theme, so the corpus Themes the reviewer owns are not changed by this PR; the knob that restores or adopts the look is the Theme declaration itself (add `border`, drop `edge`; re-add `edge` to restore). Reverse (make it a default): migrate the three corpus Themes in one PR and remove the legacy branch. A successor issue tracks retiring the legacy `edge` once the corpus Themes have migrated.

### 5.2 Ink (D2)

**Options.** (a) A literal colour in the value (bypasses the role, scheme and contrast gate; refused). (b) A role per side. (c) `kind` plus a single border role. **Chosen:** `paint: kind` draws the strip from the existing role `annotation-kind-accent` (its fill, replaced by the annotation kind's colour when the kind declares one: the existing mechanism, purpose and decoration class; the role may now be declared with only a fill, without `edge`); `paint: ink` (default) draws from a new role per side, `annotation-border-start|end|top|bottom` (a fill from the colour scheme, a decoration), so each side may have its own ink, the colour stays in the scheme and the contrast gate sees it. A declared strip whose role is missing is `E_THEME_ROLE_REQUIRED` (as artwork). A kind-painted side of a note with no kind colour takes the role's own fill.

### 5.3 Geometry (D4, D6)

Let `F` be the frame (the paint box, or the unrotated frame under tilt) and `bt, br, bb, bl` the widths. Each present side is the CSS trapezoid between the outer and padding edges, with the mitre running from each outer corner to the matching inner corner: start `[(x,y),(x+bl,y+bt),(x+bl,y+H-bb),(x,y+H)]`, end, top and bottom likewise. A trapezoid whose mitres are vertical or horizontal (the adjacent sides have width 0) is an axis-aligned rectangle and is emitted as a `Rect`; otherwise as a closed polygon `Symbol` (the form a tilted box already uses). So a single bar, the accent case, is a plain `Rect` of exactly `width x box height` at the box edge (rows 1, 2, 5), the outer edge of every strip lies on the box edge, and its extent along that edge is the box's full side (the polygon's bounds are the strip's rectangle).

- **Inset from inside the border.** The effective content inset on each side is `border + contentInsetEm`. The text origin, the kind frame's content box (bar, stamp, legacy accent, header), the wrap bound and the box size all read these four sums, so nothing sits between a border and the box edge (row 4), and every text line is at least `border + inset` from each bordered side (row 3). Box outer size = content + inset + border.
- **`fill` (#1051).** The inline `chrome` is `visuals + kind insets + (bl + inset_left) + (br + inset_right)`: the border widths enter the one sum, with no second rule. A filled box still has the slot's extent; the body wraps in what the borders and insets leave.
- **Content-sized notes.** As content insets today, the border is added after the wrap (the wrap bound is unchanged); use `fill` for a slot-exact box.
- **Tilt.** Strips are frame elements: they are rotated with the frame (`rotate_shape`, extended to polygons), and `fill`'s tilt solve sees the border in `chrome` and in the frame height.
- **Artwork (#848).** Paint order is box, artwork, **border**, kind frame, text: the artwork fills the whole paint box (it is the paper's ink, background-clip border-box) and the border is drawn over its rim.
- **Leaders and search.** The border is inside the outer bounds the search, collision and leader ports already use; the leader ends on the outer edge, which is the border's outer edge.
- **Label visuals.** Leading and trailing icons stand inside the border (the border-left is added to their start). Today they ignore the content inset; the same correction is made for the content inset only if it is byte-neutral for the corpus (checked), otherwise it is left and recorded.
- **Contrast.** Borders are decoration strips judged like the accent; note text is judged against the note box only, so a border never becomes a text ground, and no floor, class or code changes.

### 5.4 Outlines and radius (D5)

Borders are admitted on `outline: rectangle` with `cornerRadius: 0`. `balloon` (a tail is part of the outline), `image` (the artwork supplies the frame) and a rectangle with `cornerRadius > 0` with `border` are rejected: the schema refuses the combination and the token reader raises `E_THEME_TOKEN_TYPE` at `/body/roles/<role>/annotationContainer/border`. **Why the radius is rejected, not followed:** a rectangle container's `cornerRadius` is validated but not drawn today (the box is a square `Rect`); a border that followed a radius would be drawn around a square paper, and rounding the paper is a separate behaviour change to every rectangle container that declares a radius. So #1049's "border follows the rounded outline" is narrowed with a successor issue (draw the rectangle container's radius, then follow it with the border); reverse: lift the schema and reader rule when that lands. Typst and TikZ see nothing new: the strips are completed Rects and polygons.

### 5.5 Schema and compatibility (Specification 56 section 3.2)

`border` is an optional property of the `annotationContainer` value object (`additionalProperties: false`), added in place to the live Theme schemas that carry the token (v0.11 and v0.13), plus four optional role names are plain role keys (no schema change, only the capability registry). Omission keeps today's behaviour, so no version bump; a schema `default` does not implement a runtime value (the reader supplies `ink`). The reader validates the same facts again. The S0 gate `python -m tools.schema_equivalence --base-rev origin/main` runs in the code PR with expected-delta entries for this PR's own pointers; aged entries are retired with `--prune-stale`.

### 5.6 Adapters

Layout completes every strip; Scene carries a `Rect` or a polygon `Symbol`; SVG, PNG (from SVG), PDF, Typst, TikZ and the baseline visual profile draw them like any other box primitive, with no capability to omit and no fidelity downgrade (no gradient, shadow or stroke is involved: a flat fill). No adapter decides a mitre.

### 5.7 Target B adoption (D7)

The reviewer's target B Theme replaces `kind-accent-edge` and the role's `edge` with `border: {start: {width: 3, paint: kind}}` in `note-container` (the reviewer adopts the knob in PR #1061; this work edits no `examples/halcyon-1` file). Row 7 ("regenerate target B") is evidenced by synthetic Scene tests and a Controller Z slide through YAML and narrowed with the reviewer-adoption successor, as #1051 did. Corpus output is not an oracle.

### 5.8 Failure behaviour and extension points

Wrong shape or value is `E_THEME_TOKEN_TYPE`; a side whose role is missing is `E_THEME_ROLE_REQUIRED`. Extension points: the same `border` object and `annotation_border` strip functions for the as-of chip, legend boxes and table cells (not designed here); dashed or double styles are out of scope.

## 6. Architecture review

- **Layers.** Theme declares, Layout completes geometry, Scene carries, adapters serialize; one new pure Layout module, the View untouched.
- **One path.** The strip function is shared by border and the legacy accent; there is one chrome sum for content and `fill`.
- **No gate weakened.** Colours come from roles in the scheme; decorations warn, text over the box stays blocking.
- **Defaults.** No `border` means no code path; `edge` Themes are drawn as today; corpus Scene and SVG byte-identical (conformance, materializer check).
- **Adjacent designs.** #1051 (chrome), #848 (paint order), #584 (tilt, kind frame), #466 and #465 (balloon, image refused), #1044 and #1060 (untouched files). Specification 56 section 3.2 applies and is met.
- **Compatibility.** A Theme that declares `border` changes (its purpose); one that does not, does not.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **I1049-1** | new `layout/annotation_border.py`; `surface_annotations.py`; `annotation_kind_frame.py` (shared strip); `annotation_tilt.py` (polygon rotation); `theme_tokens.py`; `semantic_registry.py`; `scene/capabilities.py`; `scene/v05_builder.py`; both Theme schemas; expected deltas; Specifications 07 and 08 | each side, two sides, mitre, width 0, rejected outlines and radius, ink roles and kind colour, inset from inside, `fill` with borders, tilt, artwork order, leader, default byte identity, legacy accent unchanged | diagnostics and coverage ledgers (bot) | one code PR |
| **Evidence** | new Controller Z slide `annotation-border` (context, view, Theme, Layout, manifest row, ledger row; no existing corpus datum edited): the corpus witness the contrast gate needs for the four new decoration roles | images read; every existing corpus Scene byte-identical | the slide's Scene and SVG (bot) | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1049-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks.** Border size not added to the inset; start side on the wrong edge; strip shorter than the side; mitre dropped (rect corners overlap); width 0 emitting a primitive; border painted before the box or after the kind frame; border omitted from `chrome` (`fill` overflows); ink role ignored; kind colour not applied; accent legacy path altered; polygon not rotated under tilt; balloon, image or radius not rejected; default path entered without the property. Each must fail at least one test.

**Order and risk.** If implementation exposes a rule beyond section 5 the slice stops and the cause is recorded here before code resumes.

## 8. Progress and evidence

**Design** merged as PR #1076. **I1049-1 (Refs #1049).** `annotationContainer.border` (Theme, `theme_tokens.py`, both live Theme schemas, S0 gate PASS with two L1 entries per schema; stale entries retired with `--prune-stale`); pure geometry in `layout/annotation_border.py` (`resolve_border`, mitred trapezoids, `side_strip` shared with the content-box accent); `surface_annotations.py` folds the four border widths into the effective content insets (so text origin, kind frame content box, wrap, `fill` chrome and box size read one sum), places the strips after the artwork and before the kind frame, rotates them with the frame, and moves a label visual in by the start border; four registry roles and capabilities (`annotation-border-start|end|top|bottom`); `rotate_shape` handles a polygon strip; the Scene builder draws a `Polygon` strip as a `Symbol` like a tilted box; `annotation_kind_frame()` treats `annotation-kind-accent` without `edge` as ink only. Specifications 07 and 08 state the rule. Two choices made while coding, inside the approved contract: an unmitred strip is a `Rect` and a mitred one a polygon (decided by the four corners, not by side); the icon offset correction is the border width only (the content-inset gap of label visuals is not touched, so corpus bytes stay identical).

Tests (synthetic, no `examples/`): `tests/integration/test_annotation_border.py` (each side, mitre, width 0, inset from inside, nothing before the border, ink and kind colour, missing role, refused outlines and radius, malformed values, `fill`, tilt, paint order with artwork and kind frame, leader, legacy accent, label visuals) and `tests/unit/chrona/presentation/model/test_annotation_border_token.py`. 18 mutations (inset sum dropped or partial, start strip off the edge, strip short, mitre dropped, width 0 emitting, border below the box, `fill` chrome without the border, ink role ignored, kind paint ignored, legacy accent strip moved, polygon not rotated, reader accepting a radius or an outline, empty border non-empty, visual ignoring the border, mitred and unmitred shapes swapped, accent-without-edge check dropped) were each killed.

Evidence: `regenerate_public_examples.py --check --jobs 4` PASS for 54 slides (no corpus Theme declares `border`: byte-identical); conformance passes except the generated ledgers (`diagnostic-inventory`, `presentation-coverage`, `presentation-contrast`) that the derived snapshot regenerates. The contrast gate (`E_PRESENTATION_CONTRAST_DECORATION_WITNESS`) requires every decoration role to be enabled in committed Scene evidence, so the first CI run failed until the Controller Z slide `annotation-border` was added (a note with a kind start border and three ink sides, a callout with an ink start border, both filling a 330 px rail; the image of it was read). Controller Z through `chrona render` with a scratch copy of the corpus (a right-hand 330 px rail, `fill`, scratch Theme and Layout, no `examples/` edit), four variants read as images: today's `edge` accent (short, inside the inset, touching the text), `border.start {3, kind}` (flush with the box edge, full height, a clear text gap), start 6 kind plus top, bottom and end ink sides (mitred corners visible), and the same with a tilt cycle (strips rotate with the frame).
