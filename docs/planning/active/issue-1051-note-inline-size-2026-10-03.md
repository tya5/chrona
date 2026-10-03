# Issue #1051: note boxes fill the notes rail (`inlineSize: fill`) and wrap (work record)

Living record for [#1051](https://github.com/tya5/chrona/issues/1051) (P4-B on the [#454](https://github.com/tya5/chrona/issues/454) board, read only; target B): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #1051 (options, choice, why, how to reverse).

**Public base:** `8395aa9e` on `main`. **Status:** design plan, design, architecture review and implementation plan published together in one docs PR before code. One code slice (I1051-1) implements it, section 7.

## 1. Published baseline

#1051 has a body and no later comment (the only comment is this work's claim). Its ask: *in the approved HALCYON-1 mock every note box is as wide as the rail, so all notes share one right edge and wrap to two lines; the renderer sizes each note to its text (300.5, 299.0, 307.9 px in target B), so the right edges are ragged; add a general `inlineSize: content | fill` declaration for annotation boxes placed in a slot; `fill` takes the full inline size of the slot; the body wraps (if allowed) to that width minus kind insets, content insets and borders (#1049); start alignment is kept; `content` is unchanged; `fill` outside a slot is rejected or degrades to `content` with a warning (pick one); where the declaration lives is the implementer's choice, justified in the PR; a maximum line count is out of scope.* Read on `8395aa9e` from [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py), [`annotations.py`](../../../src/chrona/presentation/layout/annotations.py) (`annotation_rail_candidates`), [`annotation_kind_frame.py`](../../../src/chrona/presentation/layout/annotation_kind_frame.py), [`annotation_tilt.py`](../../../src/chrona/presentation/layout/annotation_tilt.py), [`text.py`](../../../src/chrona/presentation/layout/text.py) (`wrap_text`, `measure_text_width`), [`theme_tokens.py`](../../../src/chrona/presentation/model/theme_tokens.py) (`annotation_container`), the Theme schemas, Specifications 07 and 08, the mock `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png` (image read: three notes, one width, one right edge, a start accent, two wrapped lines), the [#584 record](issue-584-annotation-kinds-2026-10-02.md) and #1049 and #1050 (both open, neither designed yet):

1. **Box width is content-sized.** `place_annotations` measures the body (`text_width = max(line widths)`), adds the kind insets and the container's content insets, and passes `annotation_size` to every candidate. `annotation_rail_candidates` places a box at `rail.x` with exactly that width. Nothing reads the slot width except as the wrap bound.
2. **The wrap bound already is the slot.** With a slot, `text_available = slot inline size - leading/trailing visuals`; when the View's `text.wrap` is `allow` the body wraps to `text_available - kind inline insets`. The container's content insets are added afterwards, so a wrapped note with a content inset can be wider than the slot today (it then fails the rail rung and takes visible overflow). `fill` must wrap in what the insets leave (below).
3. **Wrap is a View intent, box look is a Theme token.** `text.wrap` (default `forbid`) is read from the anchored item's presentation. The box look (outline, radius, tail, content inset, tilt) is the Theme's `annotationContainer` token, a Layout-geometry token consumed by Layout before Scene (Specification 07); the slot's size is the Layout Profile's.
4. **Candidates.** A note's rungs are `row-aligned` (the rail slot), `nearest-free` (plot or content region, also with a balloon tail) and the adjacent `side` projection. Only the row-aligned rung places the box in the slot.
5. **Tilt (#584)** rotates the measured frame about its centre; the search sees the axis-aligned bounds of the rotated frame (`rotated_extent`), so a tilted frame as wide as the slot would not fit the slot.
6. **Leaders** attach to the nearest edge midpoint of the candidate's bounds (`nearest_box_port`); the box start edge is always `rail.x`.
7. **Evidence today.** Controller Z `annotations` rendered through `chrona render` (view `views/annotations.yaml`, theme `executive-light`, layout `annotations-review`) shows five notes of five widths in the bottom annotations slot (image read); target B has the ragged widths above.

Unverified at design time: nothing about the adapters, since the box is a completed Rect and the text are completed lines (Specification 08); confirmed by the rendered evidence in section 8.

## 2. Literal acceptance (copied from the issue, plus the assignment)

From the issue body, "Acceptance (synthetic fixtures, published Scene)":

1. With `fill`, every annotation box in a slot has an inline extent equal to the slot's inline extent, on both the start and the end edge, and all such boxes share one right edge.
2. Every body line's measured width is at most the box's inner width, which is the box minus insets and borders.
3. With `content`, the output is byte-identical to today's.
4. `fill` combined with a non-slot placement behaves as specified: rejected, or `content` plus a warning.
5. Target B, regenerated, shows equal-width notes with wrapped bodies.

From the issue body, "Proposal" asks that this record also meets: the declaration's home is justified; `fill` keeps start text alignment; the line cap is out of scope.

Assignment constraints: (a) a general Theme/Layout declaration with min/max, tilt and leader interaction, defaults unchanged, baseline profile and Typst/TikZ stated honestly; (b) synthetic tests with no `examples/` input, mutation-checked; (c) contrast gates stay (labels on note boxes are ground text); (d) rendered images are read, through a Controller Z evidence slide, not the reviewer's `examples/halcyon-1/*target-b*` YAML, which is not edited (the reviewer adopts the knob; row 5 is narrowed with a successor, section 5.9); (e) #1049, #1050 are related, separate and not absorbed; #848, #991, #1030/#1031, #911 files are avoided.

## 3. Dependencies and neighbours

- Composes with, does not absorb: #1049 (per-side box border: its widths join the box chrome that `fill` subtracts), #1050 (viewer-fit mode: `text-follows-box` uses each line's measured width, which `fill` leaves alone; `box-follows-text` is incompatible with a fixed width, section 5.7).
- Reused unchanged: #584 (kind frame, tilt), #466 (candidates, balloon, in-plot notes), #493 (text measurement: the same `measure_text_width` and `wrap_text`), #889 (region frame: not involved).
- Files owned by this change: a new `layout/annotation_inline_size.py` (pure arithmetic), a few lines in `surface_annotations.py` and `theme_tokens.py` (the token fields), the live Theme schemas, tests, Specifications 07 and 08, the diagnostics message and ledger. #848 (annotation artwork) is another agent's: the diff in shared files is kept to the call sites and appended token fields; if it collides, rebase onto #848.

## 4. Design plan

| Id | Use case | Source |
| --- | --- | --- |
| U1 | A Theme makes every note of a role as wide as the notes slot, so the notes form one aligned column; the body wraps in what the insets leave. | #1051 |
| U2 | A Theme caps that width (a narrower column inside a wider slot); the column stays start-aligned. | assignment (min/max) |
| U3 | A short body keeps the full width; a long body wraps and the box grows in block size only. | assignment |
| U4 | A tilted note takes the width at which its rotated bounds fit the slot. | #584 |
| U5 | A note that falls back to a plot, content or adjacent rung keeps content sizing and says so. | #1051 row 4 |
| U6 | A Theme that does not declare it renders byte-identically. | #1051 row 3 |

Open decisions (decided in section 5, recorded on #1051): **D1** where the declaration lives; **D2** what `fill` means with wrap forbidden, unbreakable text and a header; **D3** non-slot behaviour; **D4** min and max; **D5** tilt; **D6** leaders; **D7** composition with #1049 and #1050; **D8** how target B adopts it.

Responsibility boundary: the View owns whether a body may wrap (`text.wrap`; absent means allow only under `fill`) and the slot owns its size (Layout Profile); the Theme owns the box's sizing behaviour next to its other geometry (outline, insets, tilt); Layout owns the measured width, wrapping and placement; Scene carries the completed Rect and lines; adapters serialize. Data model: two optional properties on the existing `annotationContainer` token value; no Scene member, no View or Layout Profile change. Migration: none, omission is today's output. Design review questions: can a declaration move a leader or a gate? Does the default stay byte-identical? Does a fallback rung ever receive a slot-wide box? Does the rule need a schema version bump (Specification 56 section 3.2)?

Acceptance evidence: synthetic tests (section 7), mutation checks, conformance and the corpus unchanged (byte identity), a Controller Z rendered image read, the S0 gate.

## 5. Design

### 5.1 The declaration (D1)

On the `annotationContainer` token value (rectangle, balloon and image outlines alike):

```yaml
annotationContainer:
  outline: rectangle
  cornerRadius: 0.2
  inlineSize: fill        # content (default, today) | fill
  maxInlineEm: 32         # optional, number > 0, only with fill
```

**Options.** (a) The Theme token (chosen). (b) A Layout Profile `annotations` slot property. (c) A View annotation property.

(b) is where the width lives, but a slot is shared by every annotation role (callout, note, highlight, arrow) and by roles that are not boxes, and a Layout Profile cannot see the kind frame or content insets that make up the chrome `fill` subtracts; it would also add a second place that sizes a box (the token already owns the insets and tilt that change the size). (c) puts presentation in the View. The issue says the rail width is layout and the box look is Theme; sizing a box to its slot is box look (it is a per-role CSS-like `width: 100%` and composes with the border and viewer-fit declarations, which are also box-role Theme declarations). It is read per annotation role, so a Theme can fill notes and keep callouts content-sized.

Reverse: remove the two properties; no data depends on them.

### 5.2 What `fill` computes (D2)

For a note placed on the row-aligned rung, with `S` = the slot's inline size and `chrome` = kind inline insets + content insets (left + right) + (#1049) border widths + leading and trailing visuals:

- `outer = S`, or `min(S, maxInlineEm * annotation text size)` when `maxInlineEm` is declared (D4).
- Wrap bound `= max(1, outer - chrome)`. Lines come from the same `wrap_text` with the same text treatment, font metrics, letter spacing and transform as `content` (the #493 measurement); the View intent decides whether it wraps (next bullet).
- **Wrap authority.** `text.wrap` is a per-item View intent, and it is reachable only through `rows.mode: explicit` (`items[].presentation`, or the row's); under `rows.mode: automatic`, which target B uses, no item carries an intent and the effective value is today's `forbid`. A filled box whose body cannot wrap cannot meet its own width, so for a note whose container declares `fill` an absent intent means `allow`; an explicit `text.wrap: forbid` is honoured (one line, 5.2 last paragraph). Without `fill` an absent intent stays `forbid`, as today. (A View-level default for notes would be a separate owner question and is not designed here.)
- Box inline size `= max(outer, widest line + chrome, kind header inline + kind insets + content insets)`. In every ordinary case this is `outer`.
- Box block size is the content formula, from the wrapped line count. Text keeps its start alignment: the body starts at the box start plus insets; nothing is centred or justified.
- The box starts at the slot's start (`rail.x`), so with `maxInlineEm` a narrower column shares one start edge and one right edge, and without it also the slot's end edge.

**Shorter text:** the box keeps the full width; the body occupies the start of it. **Longer text:** it wraps and the box grows in block size only. **Unbreakable text, a kind header or a body with `text.wrap: forbid` wider than `outer`:** the box takes that wider size, exactly the visible-overflow path a content box takes today (the rail rung fails to fit and the existing fallback ladder and diagnostics apply). `fill` never clips, shrinks or truncates text; the body-width criterion (row 2) holds whenever the View allows wrapping and every word fits, and the header and forbid cases are the documented exceptions, not silently degraded. A maximum line count stays out of scope (#1051).

### 5.3 Fallback and non-slot placement (D3)

**Options.** (a) Reject `fill` with a non-slot placement; (b) degrade to `content` with a typed warning (chosen).

A Theme is reusable across Layout Profiles and across a note's declared rungs (`rail` first, then a plot or adjacent fallback); an error would make the same Theme valid with one profile and fatal with another, and would make a View's fallback ladder fail in exactly the case it exists for. So: `fill` applies only when the note is placed on a row-aligned rung of an annotations slot. When it is placed on a `nearest-free` rung, an adjacent rung, or when no annotations slot exists, the box is sized as `content` from the same lines (wrapped as `content` wraps, honouring the declared candidate `maxInlineEm`), and Layout adds the diagnostic `W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:<annotation id>:<rung or none>`. The warning is part of the render diagnostics; nothing fails. Reverse: make it an error by raising `LayoutError` at the same site.

### 5.4 Min and max (D4)

`maxInlineEm` caps the filled width (`min(S, maxInlineEm * text size)`): a column narrower than the slot, start-aligned; shared start edge, shared right edge, not the slot's end edge. A `maxInlineEm` without `fill` is invalid (`E_THEME_TOKEN_TYPE` at the property, and the schema rejects it). There is no `minInlineEm`: `fill` is already the maximum available width, and a floor for `content` boxes is a different feature (a minimum for short content) that nothing asks for; if the slot is narrower than a would-be minimum the slot wins by 5.2 anyway. If a minimum is wanted later it is one more optional property with the same rule.

### 5.5 Tilt (D5)

A tilted note is searched through the axis-aligned bounds of its rotated frame (#584). For `fill`, the rotated bounds, not the unrotated frame, are what must equal `outer` on the inline axis. Layout solves the frame width `w` with `rotated_width(w, h, angle) = outer`, `w = (outer - h * |sin a|) / |cos a|`, where the frame height `h` depends on the wrap: start at `w = outer`, wrap, measure `h`, recompute `w`, and repeat while `w` shrinks (monotone, at most 16 rounds; the last pair of lines and width is always consistent). The final `w` is widened to the solved value, so the rotated bounds equal the slot width and the search and collision see the slot-wide extent. Tilted notes do not share a right edge (they are rotated) but they do share the bounds' start and end edges. The determinism of the angle (`tiltDegrees[i mod n]`) is unchanged, so two renders stay equal.

### 5.6 Leader anchors (D6)

The leader egress is computed from the candidate's bounds. The box start edge is `rail.x` with or without `fill`, so a leader from the plot lands on the same start-edge midpoint; only the top and bottom edge midpoints move (the box is wider). The route search is unchanged (bounds are an input); the leader obstacle index sees the wider rectangle, so a note may now block a corridor that a narrow one left open, and that is resolved by the existing collision and fallback ladder. A tilted note anchors to the bounds as today.

### 5.7 Composition with #1049 and #1050 (D7)

- **#1049 per-side border.** The chrome in 5.2 is one function, `box_inline_chrome`, that today sums the kind insets and content insets; #1049 adds the start and end border widths to it. The wrap bound is then `outer - borders - insets`, as the #1049 text requires, with no second rule in the fill code.
- **#1050 viewer fit.** `text-follows-box` sets each text line's `textLength` to the line's measured width in the Scene, not the box's inner width; `fill` changes neither the lines nor their widths, so they compose. `box-follows-text` draws a box whose end is decided at view time; that cannot equal a fixed filled width, so #1050's schema should reject `box-follows-text` with `inlineSize: fill` (a declaration conflict, not a silent degrade). Recorded here for #1050's design; nothing in this change depends on it.
- **Contrast.** Fill, text and gate bindings are untouched. Note text is judged against its own same-source, opaque, flat note box (Specification 08 C4): the box grows, the colours do not. Labels on note boxes stay ground text; nothing is weakened.
- **Typst, TikZ, PNG, PDF, SVG and the baseline visual profile.** `fill` is Layout geometry, not paint: Scene carries the completed `Rect` (or balloon or image Rect) at its final bounds and completed text lines, and every adapter serializes them. There is no capability to omit and no fidelity downgrade; the baseline profile (v0.5) draws the same wider rectangle and the same wrapped lines. What an adapter cannot know is the viewer's font (#362, #1050): SVG text uses a face that may be wider than the layout measurement, so a filled box has the same view-time drift risk as a content box, with more room before it overflows. No adapter re-wraps text.

### 5.8 Schema and compatibility (Specification 56 section 3.2)

Both properties are optional additions inside the existing `annotationContainer` value object (`additionalProperties: false`), added in place to the live Theme schemas that carry the token (v0.11 and v0.13, as #991 did for `contentInsetEm`); omission keeps today's behaviour, so no version bump. A schema `default` annotation does not set a value; the token reader supplies `content`. The reader validates the same facts again (`E_THEME_TOKEN_TYPE` at `/body/roles/<role>/annotationContainer/inlineSize` or `.../maxInlineEm`). The S0 gate `python -m tools.schema_equivalence --base-rev origin/main` runs in the code PR; the expected-delta entries are written for this PR's own pointers only and aged entries are retired with `--prune-stale` guidance. Specification 07 states the rule; Specification 08 states that Scene geometry is complete.

### 5.9 How target B adopts it (D8)

The reviewer's `examples/halcyon-1/themes/target-b.yaml` adds `inlineSize: fill` to its `note-container`, and gets wrapping from the absent-intent rule of 5.2 (no `text.wrap` is needed, because target B's automatic rows cannot carry one). This change edits neither (the reviewer adopts the knob, per the assignment). Row 5 ("target B, regenerated") is therefore not claimed from the corpus: it is evidenced by synthetic Scene tests and a Controller Z slide through YAML, and the acceptance review marks it narrowed with a successor issue for the reviewer's adoption step (searched for duplicates before filing). Corpus output is not an oracle.

### 5.10 Failure behaviour and extension points

Wrong type or value is `E_THEME_TOKEN_TYPE`; non-slot is a warning (5.3); text wider than the slot is the existing visible overflow (5.2). Not designed: a minimum, a maximum line count (the owner is deciding layout-time fitting), `fill` for other box roles (chip, legend, table cell; the property name and rule are the extension point).

## 6. Architecture review

- **Layers.** Theme declares, Layout computes (one new pure module plus call sites), Scene and adapters unchanged. The View's `text.wrap` stays the only wrap authority; the Theme never wraps.
- **No second path.** One chrome function and one wrap call serve content and fill; fill differs only in the target width.
- **No gate weakened.** No contrast floor, class or code changes; the box colour is unchanged. Row 2 is a test, not a hope: a body line wider than the box inner width cannot be produced when wrapping is allowed.
- **Defaults.** Without the property the code path is not entered; the corpus Scene and SVG are byte-identical, checked by conformance and the materializer check.
- **Adjacent designs.** #584 (frame and tilt), #466 (rungs, balloons: a balloon with a tail is placed on a nearest-free rung, so `fill` degrades and warns there), #889 (untouched), #493 (same measurement), #1049 and #1050 (5.7). Specification 56 section 3.2 applies and is met (5.8).
- **Corpus evidence is not an oracle.** No corpus datum is edited. The rendered Controller Z slide and target B are read as evidence against the mock.
- **Compatibility.** A Theme that declares the property changes (that is its purpose); a Theme that does not, does not.

## 7. Implementation plan

| Slice | Files | Tests (synthetic, no `examples/`) | Generated | Publication |
| --- | --- | --- | --- | --- |
| **I1051-1** | new `src/chrona/presentation/layout/annotation_inline_size.py` (fill measure, tilt solve); `surface_annotations.py` (measure a content variant and a fill variant, choose per rung, warn on non-slot); `theme_tokens.py` (`inline_size`, `max_inline_em` appended to `AnnotationContainerToken`, validated); `schemas/theme-v0.11.schema.yaml` and `theme-v0.13.schema.yaml`; the expected-delta entries; `diagnostic_messages.py`; Specifications 07 and 08; new `tests/integration/test_note_inline_size.py` and unit tests of the measure | rows 1 to 4, tilt, max, fallback warning, forbid and header cases, #1049-style chrome | the diagnostics inventory (bot-regenerated) | one code PR |
| **Evidence** | none | a Controller Z slide through YAML (a scratch Theme that declares the knob), image read; conformance and the corpus byte-identical | none | in the PR |
| **Acceptance** | `docs/reviews/current/issue-1051-...` | literal rows | none | one docs PR, then the exact-main three-OS run |

**Mutation checks (I1051-1).** Fill ignored (content width); the end edge short of the slot; the wrap bound not reduced by content insets, by kind insets, by visuals; the max ignored; the max applied without fill; the non-slot warning dropped; fill applied on a non-row-aligned rung; the tilt solve replaced by the unrotated width; the header or unbreakable word clipped to the slot; the default path entered without the property. Each must fail at least one test.

**Order and risk.** If implementation shows a rule beyond section 5 is needed (for instance the rail candidate search relying on the content width), the slice stops and the cause is recorded here before code resumes.

## 8. Progress and evidence

**Design** merged as PR #1052. **I1051-1 (Refs #1051).** `annotationContainer.inlineSize: content | fill` and `maxInlineEm` (Theme, `theme_tokens.py`, both live Theme schemas, S0 gate PASS with six L1 entries for this change); the pure fill arithmetic in `layout/annotation_inline_size.py`; `surface_annotations.py` measures a content variant (the unchanged path, moved into one local `measure_note`) and, only when `fill` is declared in a slot, a fill variant, picks the fill variant on a row-aligned rung (and on the rail visible-overflow fallback) and otherwise warns `W_LAYOUT_ANNOTATION_FILL_NOT_SLOT`. Specifications 07 and 08 state the rule. Two choices made while coding, inside the approved contract: the fallback `place_annotation_rail` also takes the fill size (same slot), and a trailing label visual stands at the filled box's end edge.

Tests (synthetic, no `examples/`): `tests/integration/test_note_inline_size.py`, `tests/unit/chrona/presentation/layout/test_annotation_inline_size.py` and `tests/unit/chrona/presentation/model/test_annotation_inline_size_token.py`. 13 mutations (fill never computed, box not widened to the slot, box clipped to the slot, content insets, kind insets or visuals dropped from the chrome, maximum ignored, maximum accepted without fill or at zero, non-slot warning dropped, tilt solve replaced by the unrotated width, default path entered without the property, trailing visual off the end edge) were each killed, four of them after strengthening a test.

Evidence: conformance passes except the two generated ledgers (`diagnostic-inventory`, `presentation-coverage`), which the derived snapshot regenerates; `tools/regenerate_public_examples.py --check --jobs 4` reports PASS for 54 slides (no corpus Theme declares the property, so output is byte-identical). Controller Z `annotations` through `chrona render` with a scratch Theme and a right-hand 360 px rail (scratch YAML, no `examples/` edit): content gives three boxes of three widths with ragged right edges; fill gives three boxes with one start and one right edge; at a 250 px rail with `tiltDegrees [-1.5, 1.5]` the third note wraps to two lines and the rotated bounds fill the rail (images read).
