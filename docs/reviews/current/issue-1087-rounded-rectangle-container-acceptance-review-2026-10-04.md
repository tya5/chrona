<!-- chrona:literal-acceptance/v1 -->

# Issue #1087: rounded rectangle annotation container and its following border, acceptance review

Source: [Issue #1087](https://github.com/tya5/chrona/issues/1087), re-fetched 2026-10-04 after the code merge (body unchanged since filing; the comments are this work's claim with the owner-level decisions and status blocks; no new rows). The rows are the literal acceptance bullets of the body and the lead's added constraints. Work record: [issue-1087-rounded-rectangle-container-2026-10-04.md](../../planning/active/issue-1087-rounded-rectangle-container-2026-10-04.md); living contract [Specification 07](../../specification/07-style-and-theme.md) (rounded rectangle container) and [Specification 08](../../specification/08-scene-and-rendering.md).

Slices: design [PR #1103](https://github.com/tya5/chrona/pull/1103) (`4e07e332`); I1087-1 (rounded outline geometry, Layout call sites, reader and schemas, specifications, Controller Z slide, tests) [PR #1113](https://github.com/tya5/chrona/pull/1113) ([`d5bf6228`](https://github.com/tya5/chrona/commit/d5bf62280b00bba42630b5f34c0ec5ed950a8409)), CI green before merge.

## Literal issue acceptance

### Issue #1087

- Source: [Issue #1087](https://github.com/tya5/chrona/issues/1087)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A rectangle with `cornerRadius > 0` renders rounded paper. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py) `test_a_rectangle_with_a_radius_draws_rounded_paper` (the box `Rect` carries `corner_radius` = radius em x text size), `test_the_radius_is_clamped_to_half_the_shorter_side`, the SVG `rx` in `test_svg_draws_the_radius_and_the_quadratic_strip_and_png_pdf_follow_the_svg`; the committed slide [`annotation-rounded`](../../../examples/controller-z/generated/annotation-rounded.svg) (full slide and 3x crops read as images). A tilted note is a rotated rounded path (`test_a_tilted_rounded_note_is_a_rotated_rounded_path_with_rotated_strips`). | none |
| 2 | A bordered one has per-side strips following the outline. | met | `test_a_single_side_follows_the_rounded_outline` (each of the four sides: the strip is a polygon of arcs on the paper with its outer edge on the box edge), `test_two_sides_follow_the_outline_and_meet_in_a_mitre`, `test_four_sides_leave_the_padding_outline_rounded_inside`; the pure geometry in [`test_rounded_outline.py`](../../../tests/unit/chrona/presentation/layout/test_rounded_outline.py) `test_the_strips_tile_the_ring_between_the_two_outlines` (six width and radius cases, a grid of points: each ring point is in exactly one strip, no other point is in any). Decision recorded: full CSS ring segments, not a restriction (work record 5.2). | none |
| 3 | Fixtures for each side, two sides, tilt, artwork and `fill`. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py): Each side and two sides: rows above; tilt: `test_a_tilted_rounded_note_is_a_rotated_rounded_path_with_rotated_strips` (two angles, with `fill`); artwork: `test_artwork_stays_over_the_rounded_paper_unclipped_and_under_the_border` (box, artwork, border order); `fill`: `test_a_filled_rounded_note_keeps_the_slot_extent_and_wraps_inside_the_border`. | none |
| 4 | The schema and reader rule from #1049 (refuse `border` with a radius) are lifted. | met | `test_a_border_is_admitted_with_a_corner_radius` in [`test_annotation_border_token.py`](../../../tests/unit/chrona/presentation/model/test_annotation_border_token.py); both live Theme schemas drop the `cornerRadius: const 0` consequence (S0 gate with one L1 entry per schema, [expected deltas](../../../conformance/schema-equivalence/expected-deltas-v0.1.yaml)); balloon and image are still refused (`test_balloon_and_an_empty_border_are_refused_by_the_schema_not_ignored`). | none |
| 5 | (Lead) Typst and TikZ stated honestly. | met | [Specification 08](../../specification/08-scene-and-rendering.md) and work record 5.4: a rounded paper is a `Rect` with a radius, which Typst (`radius`) and TikZ (`rounded corners`) draw; a strip is a `Symbol`: TikZ draws its quadratic outline (one control point repeated as both cubic controls, a few percent bulge on a short arc), Typst refuses any surface with a `Symbol` (`E_VISUAL_CAPABILITY_UNSUPPORTED`), exactly as for a tilted box, a balloon and #1049's mitred strips (`test_typst_draws_rounded_paper_and_refuses_a_strip_symbol_while_tikz_draws_both`). Nothing was compiled with Typst or TikZ here. **Correction to the #1049 review:** its row 12 and Specification 08 said Typst drew the strips unchanged; that was wrong for Typst and is corrected here. | none |
| 6 | (Lead) Contrast grounds stay correct (the paper shrinks at the corners). | met | Layout guarantees every inset is at least `R (1 - 1/sqrt 2)` (`test_text_is_inset_by_at_least_the_corner_clearance_so_it_stays_on_the_paper`: no content inset, no border, radius 1.5 em, the text corners are inside the rounded outline; `test_a_small_radius_keeps_the_larger_declared_inset`); note text is judged against the note box by its centre as before; strips are decorations; no floor, class or code changed. The derived contrast report ([presentation-contrast.md](../../diagnostics/presentation-contrast.md)) shows no corpus error with the new slide. | none |
| 7 | (Lead) Composes with viewer-fit (#1050) and leaders. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py): `test_text_follows_box_composes_with_a_radius_and_box_follows_text_stays_refused` (the existing #1050 rule `cornerRadius` > 0 refuses `box-follows-text`, unchanged); `test_a_leader_ends_on_a_straight_edge_of_the_rounded_box`; a tilted rounded note's leader attaches to the sampled rounded outline. | none |
| 8 | (Lead) Defaults byte-identical; corpus regenerated and reviewed if a committed Theme declared the ignored radius. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py): No committed Theme declares a rectangle radius above 0, so no slide changes: `regenerate_public_examples.py --write` changed only the new slide's files (61 existing slides byte-identical, no grouped diff, no unread image); `test_a_theme_without_a_radius_is_byte_identical` and `test_a_note_with_no_container_is_a_square_box_with_no_radius`. Knob to restore the square box: `cornerRadius: 0`. | none |
| 9 | (Lead) Synthetic tests with no `examples/` input, mutation-checked. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py): 20 integration, 12 geometry and the token tests; none reads `examples/`; 14 mutations (paper radius, clamps, tilt outline, strips square, padding arc, radii swapped, mitre cuts, clearance, refusal restored, default drawing a radius, quadratic controls not rotated, one 90-degree quadratic per corner) were each killed, one after adding a test. | none |
| 10 | (Lead) The reviewer's target-B YAML and #454 are not touched; nothing else retired. | met | [`test_rounded_container.py`](../../../tests/integration/test_rounded_container.py): `git diff --stat` of both PRs lists no `examples/halcyon-1` file; #1088 (retire the legacy `edge` accent) stays open. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares, Layout completes the outline and strips, Scene carries `Rect(corner_radius)` and polygon `Symbol`s, adapters serialize. Schema: one in-place relaxation (Specification 56 section 3.2). Disclosures:

- **Decision D3** (full CSS ring segments): reverse by refusing `border` with a radius.
- **Clearance floor** (insets at least `R (1 - 1/sqrt 2)`): changes the box size of a rounded note whose insets are smaller than that; reverse by dropping the floor (text could then stand over the corner).
- **Artwork is not clipped** to the rounded paper.
- **Not verified:** Typst and TikZ output compiled; viewers other than resvg.

Exact review-bearing-main three-OS CI must pass before closing #1087; that run is recorded in the closing comment.
