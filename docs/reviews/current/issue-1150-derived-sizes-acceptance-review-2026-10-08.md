<!-- chrona:literal-acceptance/v1 -->

# Release review — derived sizes (track, axis and header, chips)

Implementation: [#1187](https://github.com/tya5/chrona/pull/1187) (track from the row), [#1210](https://github.com/tya5/chrona/pull/1210) (track = row less a padding on each side), [#1211](https://github.com/tya5/chrona/pull/1211) (axis from its lanes, header from the axis), [#1213](https://github.com/tya5/chrona/pull/1213) (chip minimum block size). Plan and decisions: [Status comment](https://github.com/tya5/chrona/issues/1150#issuecomment-6044113536). Every PR: `tools/regenerate_public_examples.py --check` PASS (67 slides, 0 changed), S0 `schema_equivalence --base-rev origin/main` PASS, synthetic tests with no `examples/` input, one mutation check each.

Reviewer finding (target B shifts about 1.3 px horizontally when `timeline.mark.blockSize` is dropped): the unbound track was 19, not 16, and the plot's inline end reserve depends on the mark size. [#1210](https://github.com/tya5/chrona/pull/1210) derives row less twice the padding; a scratch copy of target B without the binding now derives 16 and renders a byte-identical SVG and 0 of 359 changed Scene bounds ([evidence](https://github.com/tya5/chrona/issues/1150#issuecomment-6048199811)).

## Literal issue acceptance

### Issue #1150

- Source: [Issue #1150](https://github.com/tya5/chrona/issues/1150)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Changing the row height moves the track size with no other edit. | met | [test_derived_sizes.py](https://github.com/tya5/chrona/blob/a857ea26397cfb2b72552ec500c6108b5c9cbf27/tests/integration/test_derived_sizes.py): row 40 and 60 give tracks 24 and 44, the padding moves it too, a derived track equals the declared one primitive for primitive (including every inline position at row 22 / padding 3), a bound track wins, a row that leaves no track is `E_LAYOUT_METRIC_REQUIRED`. [Unit rule](https://github.com/tya5/chrona/blob/a857ea26397cfb2b72552ec500c6108b5c9cbf27/tests/unit/chrona/presentation/layout/test_sources.py). Spec 24 derived-sizes paragraph. | — |
| 2 | The table header's bottom equals the axis bottom. | met | [test_derived_sizes.py](https://github.com/tya5/chrona/blob/a857ea26397cfb2b72552ec500c6108b5c9cbf27/tests/integration/test_derived_sizes.py): an unbound axis is the lane sum (24 + 22) and the header follows it, equal to an explicit render byte for byte; a lane edit moves the axis rule and the first row together; a bound axis and header win. [test_axis_lanes.py](https://github.com/tya5/chrona/blob/a857ea26397cfb2b72552ec500c6108b5c9cbf27/tests/unit/chrona/presentation/layout/test_axis_lanes.py): lane stack, band stack, and a rotated labels tier stays required. | — |
| 3 | The chip height equals line height + 2 × padding, or `minBlockSize` when that is larger. | met | [test_chip_min_block.py](https://github.com/tya5/chrona/blob/a857ea26397cfb2b72552ec500c6108b5c9cbf27/tests/integration/test_chip_min_block.py): the natural chip is the text block plus its padding on both sides (the existing `chipPadding` rule, block side half of the inline ratio); `chipMinBlockSize` (the issue's `minBlockSize`, named for the chip role) grows a shorter chip equally above and below an unmoved text line; a smaller minimum changes nothing; a non-positive one is a token diagnostic. One `chip_padding` helper serves the member, as-of, period and finish-delta chips. Spec 39. | — |
| 4 | Swapping the artwork glyph keeps the declared padding from its inner edge. | narrowed | Lane G (annotation containers) is dev A's and the lead directed this slice off it. A finished, tested slice is parked on [`wip/issue-1150-artwork-padding`](https://github.com/tya5/chrona/commit/9271774b) (`contentPaddingEm`, schema one-of with S0 entries, Spec 07, `test_artwork_padding.py`). | [#1216](https://github.com/tya5/chrona/issues/1216) |
| 5 | Absent declarations give byte-identical output. | met | Every bundled Theme and example binds the track, axis and header and declares no `chipMinBlockSize`: `tools/regenerate_public_examples.py --check` PASS on #1210, #1211 and #1213 (67 slides, 0 primitives changed); CI `derived-preview`, `pr-conformance` and the three pytest shards green on [#1210](https://github.com/tya5/chrona/pull/1210), [#1211](https://github.com/tya5/chrona/pull/1211) and [#1213](https://github.com/tya5/chrona/pull/1213). Target B without its explicit track renders byte-identically (above). | — |

## Programme-level criteria (optional)

Target B adoption (dropping its explicit `timeline.mark.blockSize`, `timeline.axis.blockSize` and `table.header.blockSize`) is the reviewer's step, not a dev closing condition, per the reviewer's clarification on the issue; it is deferred to the reviewer's migration PR. The Theme `metrics` map and the Layout derivation stay in Layout; `{expr:}` and `{ref:}` ([#1151](https://github.com/tya5/chrona/issues/1151)) are not needed by these defaults. Schema change: one optional role property (`chipMinBlockSize`), additive under Spec 56 section 3.2, no version bump.
