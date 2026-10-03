<!-- chrona:literal-acceptance/v1 -->

# Issue #1063: as-of chip below the plot, acceptance review

Source: [Issue #1063](https://github.com/tya5/chrona/issues/1063), re-fetched 2026-10-04 after the merges (body unchanged, 1516 characters; three comments, all this work's claim, decision and status blocks, no new acceptance rows). The issue has an acceptance list; the rows below are its seven literal bullets. Work record: [issue-1063-1066-target-b-top-items-2026-10-03.md](../planning/active/issue-1063-1066-target-b-top-items-2026-10-03.md); living contract [Specification 39](../../specification/39-axis-and-observation-clarity.md) (as-of marker).

Slices: design record [PR #1067](https://github.com/tya5/chrona/pull/1067) (`a755cfd6`); implementation [PR #1078](https://github.com/tya5/chrona/pull/1078) (`be1b2d92`). The PR had conformance, three pytest shards, newest-Python reproduction and derived-ready green on its final head before merge.

## Literal issue acceptance

### Issue #1063

- Source: [Issue #1063](https://github.com/tya5/chrona/issues/1063)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `below-plot`, the chip's top is at or below the plot's bottom edge. | met | [`test_as_of_below_plot.py`](../../../tests/integration/test_as_of_below_plot.py) `test_the_chip_sits_below_the_plot_centred_on_the_rule_and_clear_of_rows_and_marks` (lane and automatic rows): the published `as-of-label` top is at or below the end of the `as-of` rule, which ends at the last row (plot rule, #880). Solver cases in [`test_asof_label.py`](../../../tests/unit/chrona/presentation/layout/test_asof_label.py). | none |
| 2 | The chip does not overlap any row, mark or legend primitive. | met | [`test_as_of_below_plot.py`](../../../tests/integration/test_as_of_below_plot.py) (same test as row 1): the chip top is at or below the bottom of every row and every `planned:` mark; the legend lies in a slot under the timeline and moves down with the reservation (row 4). The solver rejects a position that meets a mark, text, label visual or rule, and one that leaves the timeline slot (`test_below_plot_moves_beside_the_rule_when_the_centre_leaves_the_slot_or_is_taken`). | none |
| 3 | Its centre is on the as-of x. | met | [`test_as_of_below_plot.py`](../../../tests/integration/test_as_of_below_plot.py) (same test as row 1) asserts the chip's centre equals the rule's x; at a window edge the chip moves beside the rule and stays in the slot (`test_at_the_window_edge_the_chip_moves_beside_the_rule_and_stays_in_the_slot`), disclosed below. | none |
| 4 | The legend or footer moves down by exactly the reserved size. | met | `test_the_slot_below_moves_down_by_exactly_the_reserved_block` (lane and automatic rows): the legend, notes and group-details slots and the canvas move down by the chip block plus gap, which equals the value Layout computes from the Theme ([`asof_foot_reserve.py`](../../../src/chrona/presentation/layout/asof_foot_reserve.py)). A content-sized extent is a whole number of units, so the test tolerates 1 unit (observed 23.0 for 23.1); under `fill` the rows give up exactly the block (`test_under_fill_rows_give_up_exactly_the_reserved_block_in_a_fixed_surface`). | none |
| 5 | The no-room case falls back, with the diagnostic. | met | [`test_as_of_below_plot.py`](../../../tests/integration/test_as_of_below_plot.py) `test_without_room_the_chip_falls_back_inside_the_plot_with_the_diagnostic` (a fixed 70 unit timeline, both row modes) and `test_a_reservation_that_does_not_fit_leaves_the_rows_as_they_were`: the chip takes today's inside foot position and the surface carries `W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK:as-of-label` (curated cause in `diagnostic_messages.py`). An as-of outside the window reserves nothing and draws no chip. | none |
| 6 | Existing placements give byte-identical output. | met | `python tools/regenerate_public_examples.py --write` on the PR (slides under [`examples/controller-z/generated`](../../../examples/controller-z/generated)) left all 54 existing slides byte identical (only the new slide is new); [`test_existing_placements_are_unaffected_by_the_reservation_code`](../../../tests/integration/test_as_of_below_plot.py) pins `top` and `foot` canvases. Nine mutations of the reservation, fallback, centring, gap, slot bound, diagnostic and lane preflight each fail a test. | none |
| 7 | Target B declares it, and the chip no longer covers "First light". | narrowed | Owner scope rule for this work: the reviewer's `examples/halcyon-1` 21-target-b files are not edited; adopting a knob there is the reviewer's step (reviewer PR #1061, [#987](https://github.com/tya5/chrona/issues/987)). The knob exists, is documented in Specification 39 and works on the Controller Z slide `as-of-below-plot` (below). | [#987](https://github.com/tya5/chrona/issues/987) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

View declares `placement: below-plot`; Layout owns the reservation (a helper shared by the content-sized extent and row placement), the candidate set and the fallback; Scene and adapters are unchanged. One enum value in `view-v0.28` (additive; `schema_equivalence --base-rev origin/main` PASS, 12 stale expected-delta entries pruned in the PR). No Layout Profile slot was added (decision and alternatives on the issue).

Disclosures:

- Rendered image read (`examples/controller-z/generated/as-of-below-plot.svg`, regenerated by derived-sync): the chip "as of 20 May" sits one gap under the last row, centred on the dashed rule, which ends at the plot bottom; it covers no row label. Honest comparison with the mock `02-programme-board.png`: the mock's chip is an orange pill in the same position (centred under the rule end, above the legend); this slide's Theme draws plain text with no chip fill, which is the Theme's choice and not Layout's. The slide's surface has room, so the older `foot` placement did not cover a row either; the tight case where it did (target B, `fill` rows) is the fill test above.
- A4 holds up to the whole-unit rounding of a content-sized extent (observed 23.0 against a reserve of 23.1).
- Not read image by image: nothing else changed (all other slides are byte identical).

Exact review-bearing-main three-OS CI must pass before closing #1063; that run is recorded in the closing comment.
