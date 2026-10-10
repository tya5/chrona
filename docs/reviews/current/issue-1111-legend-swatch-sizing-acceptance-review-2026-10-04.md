<!-- chrona:literal-acceptance/v1 -->

# Issue #1111: legend swatch gap, area swatch size and point swatch size, acceptance review

Source: [Issue #1111](https://github.com/tya5/chrona/issues/1111), re-fetched 2026-10-04 after the merges (body unchanged, 1967 characters; two comments, both this work's claim and status blocks, no new acceptance rows). The issue has an acceptance list; the rows below are its five literal bullets. Work record: [issue-1111-legend-swatch-sizing-2026-10-04.md](../planning/active/issue-1111-legend-swatch-sizing-2026-10-04.md); living contracts [Specification 07](../../specification/07-style-and-theme.md) and [Specification 49](../../specification/49-semantic-presentation-contract.md).

Slices: design record [PR #1112](https://github.com/tya5/chrona/pull/1112) (`798dfb0c`); implementation [PR #1125](https://github.com/tya5/chrona/pull/1125) (`23ae8322`). The PR had conformance, three pytest shards, newest-Python reproduction, mcp-floor and derived-ready green on its final head, on a base equal to the `main` tip when merged.

## Literal issue acceptance

### Issue #1111

- Source: [Issue #1111](https://github.com/tya5/chrona/issues/1111)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `swatchGap` g and slot gap G, every label starts g after its swatch's end, and every next swatch starts G after the previous label's end. | met | [`test_legend_swatch_sizing.py`](../../../tests/integration/test_legend_swatch_sizing.py) `test_a_label_starts_swatch_gap_after_its_swatch_and_the_next_entry_an_entry_gap_after` (inline and block directions): every label starts 6 after its swatch's end; inline, the next swatch starts 26 after the previous label's end (within 0.5, the measured label width); block, rows are at least 26 apart. The published slide [`legend-swatches.scene.json`](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/legend-swatches.scene.json) shows the same (planned swatch ends 803.89, its label starts 809.89; the Gate label ends 1015.53 and the next swatch starts 1041.53). `test_the_content_sized_legend_slot_measures_the_swatch_gap` shows measurement reads the same gap. | none |
| 2 | An area-role swatch has the declared inline and block size. | met | [`test_legend_swatch_sizing.py`](../../../tests/integration/test_legend_swatch_sizing.py) `test_an_area_swatch_has_the_declared_inline_and_block_size_and_marks_keep_theirs`: `calendar-closed` is 22 x 12 with `swatchInlineSize` 22 and `swatchBlockSize` 12; the mark keys keep their size. Declared as a decision below: an area key follows `swatchInlineSize` only when `swatchBlockSize` is also declared. | none |
| 3 | A point swatch has the declared size. | met | [`test_legend_swatch_sizing.py`](../../../tests/integration/test_legend_swatch_sizing.py) `test_a_point_swatch_has_the_declared_size`: the gate key is 12 x 12 with `pointSwatchSize` 12 and differs from the default; the slide's `legend-swatch:milestone` is 12 x 12. | none |
| 4 | Absent declarations give byte-identical output. | met | `python tools/regenerate_public_examples.py --check` on the PR: every existing slide byte identical (only the new slide is new); [`test_legend_swatch_sizing.py`](../../../tests/integration/test_legend_swatch_sizing.py) `test_absent_declarations_are_byte_identical_and_unrelated_roles_are_untouched`. Eight mutations (gap helper, point size, area opt-in, label origin in both directions, measurement gap, validation) each fail a test. | none |
| 5 | Target B: 22 x 12 swatches, 6 px swatch gap and 26 px entry gap, as in the mock. | narrowed | Owner scope rule for this work: the reviewer's `examples/halcyon-1` target-b files are not edited; adopting the knobs there is the reviewer's step (reviewer PR #1061, [#987](https://github.com/tya5/chrona/issues/987)). The knobs exist, are documented in Specifications 07 and 49 and produce 22 x 12 keys, 6 px and 26 px on the Controller Z slide `legend-swatches`. | [#987](https://github.com/tya5/chrona/issues/987) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares sizes on the `legend-swatch` role (three optional tokens, `theme-v0.11` and `v0.13`, additive, `schema_equivalence --base-rev origin/main` PASS); Layout owns swatch and label geometry through one `swatch_extent` and one gap helper used by both measurement and drawing; View, Scene and adapters are unchanged. A duplicate search for a successor found none; the successor of the narrowed row is the existing #987.

Disclosures:

- **Decision, not yet put to the owner (reversible).** The issue says area swatches should "take `swatchInlineSize`". Reading that literally would change every Theme that already declares `swatchInlineSize` (the committed halcyon print Theme) and need corpus regeneration and image review. Choice: an area key is a rectangle only when `swatchBlockSize` is declared, with `swatchInlineSize` (else the legacy side) as its inline size; absent, the legacy square. Reverse: apply `swatchInlineSize` to the area bucket unconditionally in `swatch_extent` (a behaviour change needing the procedure above).
- Rendered image read (`examples/controller-z/generated/legend-swatches.svg`, rasterized with the packaged fonts): the legend row shows a 22 px planned key, a 12 px diamond Gate key, a pale 22 x 12 non-working-day key, each 6 px from its label and 26 px apart; labels remain ground text. Comparison with the mock `02-programme-board.png`: the mock's keys are the same shapes at the same spacing; this slide uses Controller Z's Theme, so only the mechanism is compared.
- Typst and TikZ draw the Layout-completed rectangle and label origin (tested); as before they reject Symbol primitives, so the gate key is outside their fixture. The SVG (and PNG, PDF from SVG) carry every key.
- Not read image by image: nothing else changed (all other slides byte identical).

Exact review-bearing-main three-OS CI must pass before closing #1111; that run is recorded in the closing comment.
