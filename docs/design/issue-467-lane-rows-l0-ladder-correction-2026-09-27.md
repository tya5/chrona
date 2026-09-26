# Design Correction — Lane Label Ladder Ranking and the Chain Clause (#467)

**Corrects:** the [selected design](issue-467-collision-aware-lane-rows-design-2026-09-26.md), *Allocation* (label ladder) and *Acceptance evidence*. **Evidence:** [L0 feasibility](../research/presentation/issue-467-lane-rows-l0-feasibility-2026-09-27.md).

1. **Ladder ranking.** For each item in each candidate lane, the lane allocator evaluates:
   - `label-row-1` and `label-row-2`: a label row above the lane's mark level, aligned to the bar's start, then to its end;
   - then `end` and `start` on the mark level.

   It picks the first lane, in stable lane order, where the mark and some candidate are both free, taking candidates in that order. A lane has at most two label rows. Its block extent is the mark level plus the label rows it uses; a lane that uses none is as tall as an automatic row.

   This is the ladder the selected design named. Its order is fixed by the measured objective of fewest lanes, because same-level end labels extend inline footprints and force extra lanes.
2. **Chain clause.** Literal row 1's `structure → avionics → bus-test` on one lane requires overlapping `avionics`' actual (finish 2027-04-30) with `bus-test`'s planned start (2027-04-29). Marks may not overlap. The allocator prefers a predecessor's lane when dates and geometry permit (the selected design's chain preference), so `structure → avionics` share a lane and `bus-test` takes the next free one. The acceptance review will record row 1 as `narrowed`, citing this measured slip, unless the owner changes the data.

No schema, ownership or phase change. The phase contract remains the [phase and version correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md).
