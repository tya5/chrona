# L0 Measured Feasibility — Lane Rows on HALCYON `02-programme-board` (#467)

Evidence for the [#467 plan](../../planning/active/issue-467-collision-aware-lane-rows-implementation-plan-2026-09-26.md) and its [amendment](../../planning/active/issue-467-lane-rows-implementation-amendment-2026-09-27.md). This is a read-only measurement on published `main` (`f265d2b9`), not product code.

## Method

- **Inputs:** the completed Scene of `02-programme-board`, which gives, for each of the 26 selected items:
  - the planned, actual and missing-actual mark extents;
  - the measured title width, taken from the item's own table cell;
  - the delta width, from the Δ cell.
- **Algorithm:** group-local first-fit packing in planned-start order, with a 6 px clearance.
- **Widths:** the timeline at today's 956 px, and scaled ×1.38 to approximate the width freed by a lane-summary table.
- **Label candidates** per item:
  - (a) adjacent end or start on the mark's own level, which extends the lane's inline footprint;
  - (b) a label row above the bar, left- or right-aligned to the bar, on one of *k* staggered levels. This adds lane height but not lane count.

## Results

| Footprint model | Lanes (956 px) | Lanes (×1.38) | Chain on one lane |
| --- | ---: | ---: | --- |
| marks only (lower bound) | 12 | 12 | no |
| end or start label on the mark level first | 23 | 20 | no |
| staggered label rows first, 1 row | 19 | 16 | no |
| **staggered label rows first, 2 rows** | **12** | **12** | no |
| staggered label rows first, 3 rows | 12 | 12 | no |

1. **≤ 12 lanes is feasible with required names.** It needs the ladder to prefer two staggered label rows over end or start placement on the mark level. Adjacent end labels extend a lane's inline footprint far enough (titles are 170–234 px against bars of 50–100 px) to force 20 or more lanes. With two label rows per lane, packing reaches the marks-only lower bound of 12.
2. **The named chain cannot share one lane without overlap.** `avionics`' corrected actual finishes on 2027-04-30 (`actual.yaml`, `avionics-corrected`), after `bus-test`'s planned start on 2027-04-29. In the Scene, `actual:avionics` ends at x = 1132.4 and `planned:bus-test` starts at 1129.0, both at the same block band (206–216 versus 236–246 in separate rows today; the actual is inset inside the planned band). On one lane the two marks overlap by one day of the scale, at every width. The overlap is a data fact (a slip), not a footprint-model artefact. `structure → avionics` alone can share a lane (they touch at 1049.0).

## Consequence for the design

- The lane label ladder is ranked by the allocator's objective, which is fewest lanes and then declared order: **staggered label rows before same-level end/start**, with at most two label rows per lane. The row block extent grows by the label rows. This refines, and does not contradict, the selected design's "adjacent-end, adjacent-start, then two staggered block offsets" ladder.
- Literal acceptance row 1's chain clause (`structure → avionics → bus-test` on one lane) is infeasible on the current data without drawing overlapping marks, which the selected design forbids. Row 1 will be dispositioned `narrowed`: ≤ 12 lanes met; the chain is shown in lanes where the marks do not collide, and the measured slip is cited. The alternative would be for the owner to change the HALCYON actuals or accept actual overlap. Neither is taken silently.

The throwaway measurement script is not committed; its logic is summarized above and is reproduced by the L2 allocator tests.
