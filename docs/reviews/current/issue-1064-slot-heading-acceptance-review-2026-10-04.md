<!-- chrona:literal-acceptance/v1 -->

# Issue #1064: slot heading, acceptance review

Source: [Issue #1064](https://github.com/tya5/chrona/issues/1064), re-fetched 2026-10-04 after the merges (body unchanged, 1325 characters; two comments, both this work's claim and status blocks, no new acceptance rows). The issue has an acceptance list; the rows below are its six literal bullets. Work record: [issue-1065-1064-field-group-indent-and-slot-heading-2026-10-04.md](../planning/active/issue-1065-1064-field-group-indent-and-slot-heading-2026-10-04.md); living contract [Specification 33](../../specification/33-intent-oriented-layout.md) (slot headings), [Specification 07](../../specification/07-style-and-theme.md) (the `slot-heading` text role) and [Specification 49](../../specification/49-semantic-presentation-contract.md).

Slices: design record [PR #1093](https://github.com/tya5/chrona/pull/1093) (`a4db315b`); implementation [PR #1098](https://github.com/tya5/chrona/pull/1098) (`b733e553`). The PR had conformance, three pytest shards, newest-Python reproduction and derived-ready green on its final head before merge.

## Literal issue acceptance

### Issue #1064

- Source: [Issue #1064](https://github.com/tya5/chrona/issues/1064)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A slot with a heading emits one text primitive with the declared role, inside the slot. | met | [`test_slot_heading.py`](../../../tests/integration/test_slot_heading.py) `test_a_slot_with_a_heading_emits_one_text_with_the_declared_role_inside_the_slot` (synthetic Project with notes, packaged `executive-light` bundle with a 300 px rail beside the timeline, no `examples/` input): exactly one `slot-heading:annotations` Text, a Text primitive with the `slot-heading` role and purpose, its slot id the rail, its bounds inside the slot's, text "NOTES" (the Theme role's uppercase applied to the profile copy "Notes"), no `W_SCENE_TEXT_SLOT_ESCAPE`. The same holds on the legend, notes and summary sources (their own tests) and through Typst, TikZ and the PNG of the SVG (`test_every_adapter_draws_the_caption_as_ordinary_text`). | none |
| 2 | With `header-row`, it is vertically within the axis header band. | met | [`test_slot_heading.py`](../../../tests/integration/test_slot_heading.py) `test_header_row_places_the_caption_in_the_axis_header_band_and_notes_start_below_it`: the heading's bounds lie inside the `timeline-axis` slot's block extent and its centre is the band's centre; without a band beside the slot, `block: header-row` is `top` with `I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW` (`test_header_row_without_an_axis_band_beside_the_slot_falls_back_to_top_with_a_record`). | none |
| 3 | No content of the slot overlaps it. | met | [`test_slot_heading.py`](../../../tests/integration/test_slot_heading.py) (same test as row 2: every annotation box, text and kind primitive of the rail starts at or below the caption's bottom, and below the band) and `test_a_tall_caption_pushes_the_rail_content_below_it_not_merely_where_it_already_was` (a 90 px caption moves the rail content down by more than 50 units; without the content viewport the first note would lie under it). Legend entries, note lines and summary runs start below their caption too (`test_a_legend_slot_takes_a_heading_and_its_entries_start_below_it`, `test_a_notes_slot_takes_a_heading_and_its_lines_start_below_it`, `test_a_summary_slot_takes_a_heading_and_its_runs_start_below_it`). Seventeen mutations of the viewport, band rule, gap, content rule, role, paint, source rule, record, restore, clamp, footer-band carry, measurement and manifest each fail a test. | none |
| 4 | The heading text passes the text contrast gate. | met | [`test_slot_heading.py`](../../../tests/integration/test_slot_heading.py) `test_the_heading_is_ground_text_and_a_faint_one_fails_the_contrast_gate`: with the muted ink the gate reports no error for `slot-heading:annotations`; with an ink equal to the ground it reports an error, so the gate judges the heading as ground text (`slotHeading` is classified ground text in the registry; `test_semantic_registry_contrast.py`). On the evidence slide (muted ink on the dark title-card ground) the corpus contrast gate passes. | none |
| 5 | Absent declarations give byte-identical output. | met | [`test_slot_heading.py`](../../../tests/integration/test_slot_heading.py) `test_absent_declarations_are_byte_identical_whether_or_not_the_theme_declares_the_role` (artifact bytes equal), `test_an_absent_rail_has_no_heading_and_changes_nothing`, `test_the_manifest_names_a_heading_only_when_one_is_declared` (canonical manifest bytes without a `heading` key), and `python tools/regenerate_public_examples.py --write` on the PR left all earlier public slides byte identical. | none |
| 6 | Target B declares "Notes" with uppercase. | narrowed | Owner scope rule for this work: the reviewer's `examples/halcyon-1` 21-target-b files are not edited; adopting the knob there (the rail slot declares `heading: {text: Notes, block: header-row}`, the Theme declares `slot-heading` with `textTransform: uppercase`) is the reviewer's step (reviewer PR #1061, [#987](https://github.com/tya5/chrona/issues/987)). The knob exists, is documented and works on the Controller Z slide `slot-heading` (below). | [#987](https://github.com/tya5/chrona/issues/987) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout Profile declares copy and placement intent on a slot (an optional `heading` on `slot` and `override` in `layout-profile-v0.10`, additive; `schema_equivalence --base-rev origin/main` PASS, no stale expected-delta entries pruned); Theme declares the typography and ink in the text role `slot-heading` (the `text` role when absent); Layout owns the placement, the reserved block, the content viewport, the measurement of a content-sized slot, the cut and the omissions (`layout/slot_heading.py`); Scene carries an ordinary Text of a registered ground-text purpose; adapters are unchanged. Decisions D6 to D9 with options and reversal are on the issue.

Disclosures:

- Rendered image read (`examples/controller-z/generated/slot-heading.svg`, regenerated by derived-sync): "NOTES" (small, bold, letter-spaced capitals in the muted ink) stands at the rail's start inside the axis header band, its centre on the band's centre, and the notes below. Honest comparison with the mock `02-programme-board.png`: the mock puts NOTES at the baseline of the upper axis tier and the table header labels on the lower tier; this slide centres the caption in the whole band, because the band is the one rule that does not depend on how many tiers the View draws. Aligning to a tier baseline is additive and is not part of this issue's acceptance; it, a View-level copy override and more sources are filed as [#1100](https://github.com/tya5/chrona/issues/1100).
- Font weights available to a Theme are those of its font assets (400 and 700), so the mock's weight 600 is 700 here.
- `letterSpacing` is a ratio of the font size within [-1, 1] in Theme text roles; the mock's 0.1 em is 0.1.
- Typst and TikZ reject any Scene with markers, symbols or patterns (every slide with relations or gates), independent of this work; their caption output was checked on a spans-only slide.
- Not read image by image: nothing else changed (all other slides are byte identical).

Exact review-bearing-main three-OS CI must pass before closing #1064; that run is recorded in the closing comment.
