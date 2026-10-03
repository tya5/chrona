<!-- chrona:literal-acceptance/v1 -->

# Issue #1051: note boxes fill the notes rail, acceptance review

Source: [Issue #1051](https://github.com/tya5/chrona/issues/1051), re-fetched 2026-10-03 after the code merge (body unchanged since filing; the four comments are this work's claim, the owner-level decisions, and two status blocks; no new rows). The rows below are the five literal acceptance bullets of the body, the body's Proposal asks, and the assignment constraints. Work record: [issue-1051-note-inline-size-2026-10-03.md](../planning/active/issue-1051-note-inline-size-2026-10-03.md); living contract [Specification 07](../../specification/07-style-and-theme.md) (note inline size) and [Specification 08](../../specification/08-scene-and-rendering.md).

Slices: design [PR #1052](https://github.com/tya5/chrona/pull/1052) (`d99267d5`); I1051-1 (Theme token, Layout, schemas, tests, specifications) [PR #1056](https://github.com/tya5/chrona/pull/1056) (`70ea7ec6`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready), re-run green after the final rebase.

## Literal issue acceptance

### Issue #1051

- Source: [Issue #1051](https://github.com/tya5/chrona/issues/1051)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `fill`, every annotation box in a slot has an inline extent equal to the slot's inline extent, on both the start and the end edge, and all such boxes share one right edge. | met | [`test_note_inline_size.py`](../../../tests/integration/test_note_inline_size.py) `test_a_filled_box_has_the_slot_extent_on_both_edges_and_shares_one_right_edge` (three notes, one start edge, one end edge, width 300 = the rail; the same fixture with `content` has three widths), plus short bodies, long bodies, a balloon outline, a kind accent and a label visual, all at the slot width. Sizing is [`annotation_inline_size.py`](../../../src/chrona/presentation/layout/annotation_inline_size.py), called from [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py). A Controller Z slide with a scratch 360 px rail (image read) shows ragged boxes under `content` and one aligned column under `fill`. | none |
| 2 | Every body line's measured width is at most the box's inner width (the box minus insets and borders). | met | `test_no_body_line_is_wider_than_the_box_inner_width` (with and without content insets, at least two wrapped lines), `test_the_kind_accent_is_part_of_the_chrome_the_body_wraps_inside`, `test_a_label_visual_is_part_of_the_chrome_the_body_wraps_inside`; the wrap bound is `target - chrome` (visuals, kind insets, content insets) through the one `wrap_text` and `measure_text_width`. Border widths (#1049) join `chrome` when that issue lands; no border exists yet, so none is subtracted. Exceptions are documented, not silent: an unbreakable word or kind header wider than the slot widens the box and is never clipped (`test_a_word_wider_than_the_slot_makes_the_box_wider_and_is_never_clipped`). | none |
| 3 | With `content`, the output is byte-identical to today's. | met | `test_a_theme_without_the_property_is_byte_identical` (no container, a bare rectangle container and `inlineSize: content` give the same artifact); `tools/regenerate_public_examples.py --check --jobs 4` reports PASS for 54 public slides (no corpus Theme declares the property); the content path is the moved, unchanged `measure_note`. | none |
| 4 | `fill` combined with a non-slot placement behaves as specified: rejected, or `content` plus a warning. | met | Specified as `content` plus `W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:<id>:<rung>` ([Specification 07](../../specification/07-style-and-theme.md); owner decision D3 recorded on the issue). `test_a_note_that_is_not_in_a_slot_keeps_its_content_size_and_warns` (identical bounds to the content render, one warning per note) and `test_a_filled_note_in_the_slot_does_not_warn`. | none |
| 5 | Target B, regenerated, shows equal-width notes with wrapped bodies. | narrowed | The rule is proven on synthetic fixtures and a rendered Controller Z slide (a 250 px rail with a tilt cycle wraps the third note and its rotated bounds fill the rail, image read). The reviewer's `examples/halcyon-1/*target-b*` YAML is not edited by this work (assignment); the reviewer adopts the knob with one line, `inlineSize: fill`, in `note-container` (no `text.wrap` is needed, because an absent intent is `allow` for a filled note). The adoption and regeneration are [#987](https://github.com/tya5/chrona/issues/987) (target B end to end); the hand-off is [recorded there](https://github.com/tya5/chrona/issues/987#issuecomment-5968419905). Searched `inlineSize fill` and `target B notes rail fill` over open and closed issues: no other issue covers it. | [#987](https://github.com/tya5/chrona/issues/987) |
| 6 | (Proposal) The home of the declaration is the implementer's choice, justified. | met | Theme `annotationContainer` token; options and reasons in the work record section 5.1 and the [decision comment](https://github.com/tya5/chrona/issues/1051#issuecomment-5967997084). | none |
| 7 | (Proposal) Text keeps its start alignment; a maximum line count is out of scope. | met | `test_a_short_body_keeps_the_full_width_and_start_alignment` (text starts at the box start and is not centred); no line cap was added. | none |
| 8 | (Assignment) A general declaration with min/max, tilt and leader interaction, defaults unchanged, baseline profile and Typst/TikZ stated honestly. | met | `maxInlineEm` (`test_a_maximum_makes_a_narrower_column_aligned_to_the_slot_start`, `test_a_maximum_wider_than_the_slot_is_the_slot`); no minimum, by design (work record 5.4). Tilt: `test_a_tilted_note_has_rotated_bounds_that_fill_the_slot` and the pure solve in `test_annotation_inline_size.py`. Leaders: the start edge is the slot start, so a leader lands on the same start-edge port; only top and bottom ports move (work record 5.6). Adapters: sizing is Layout geometry, Scene carries the completed Rect and lines, so SVG, PNG, PDF, Typst, TikZ and the baseline profile draw it unchanged with no omission; viewer-font drift stays #1050's problem (Specification 07 text). | none |
| 9 | (Assignment) Synthetic tests with no `examples/` input, mutation-checked. | met | 39 tests in three files, none reads `examples/`; 13 mutations (fill never computed, box not widened, box clipped, content insets, kind insets or visuals out of the chrome, maximum ignored, maximum accepted without `fill` or at zero, warning dropped, tilt solve replaced, default path entered, trailing visual off the end edge) were each killed, four after strengthening a test. | none |
| 10 | (Assignment) Contrast gates stay; labels on note boxes are ground text. | met | No colour, floor, class or code changed; the box grows and its fill is unchanged; [Specification 08](../../specification/08-scene-and-rendering.md) states a filled box is judged as a content-sized one. The Controller Z render passed the contrast gates. | none |
| 11 | (Assignment) Rendered images were read, through a Controller Z slide, not the reviewer's target-B YAML. | met | Scratch YAML (a scratch Theme and Layout copy of `examples/controller-z`, not committed) rendered with `chrona render`: content versus fill at a 360 px rail, and fill at 250 px with `tiltDegrees [-1.5, 1.5]`, three images read; `git diff --stat` of both PRs lists no `examples/` file. | none |
| 12 | (Assignment) #1049 and #1050 are composed with, not absorbed. | met | The wrap bound is one `chrome` sum that #1049 extends with border widths; #1050's `text-follows-box` uses measured line widths that fill leaves unchanged, and the work record 5.7 states `box-follows-text` cannot combine with `fill` for #1050's schema. No border or viewer-fit property was added. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares, Layout computes, Scene and adapters are unchanged; the View's `text.wrap` stays the only wrap authority, with one stated rule for a filled note (an absent intent means `allow`, because automatic rows cannot carry the intent). Schema change is an in-place optional addition to both live Theme schemas (Specification 56 section 3.2); the S0 gate passes with six L1 entries for this change.

Disclosures:

- **Decision D3** (non-slot placement warns instead of failing): reverse by raising `LayoutError` at the same site.
- **Decision D9** (absent `text.wrap` is `allow` under `fill`): reverse by passing the declared intent unchanged to the fill measure.
- **No minimum** is provided; a content floor is a different feature.
- **Row 5 is narrowed** to the reviewer's adoption in #987; this work did not edit target B.

Exact review-bearing-main three-OS CI must pass before closing #1051; that run is recorded in the closing comment.
