# Design Correction — Lane Rows: Closure Phase, View Version and Adjacent Contracts (#467)

**Corrects:** the [#467 selected design](issue-467-collision-aware-lane-rows-design-2026-09-26.md), its suspended *Closure order* paragraph and its View version. **Resolves:** the [#467 prerequisite recheck](../reviews/current/issue-467-lane-rows-prerequisite-recheck-2026-09-26.md). **Common contract:** the [#466 route-priority correction](issue-466-general-placement-route-priority-correction-2026-09-26.md). **Handoff:** owner-approved takeover by the dev B session, 2026-09-27.

## 1. Closure phase: lane names are required text

The #466 correction fixes the one Layout phase contract:
1. slots, rows, marks, ports, rule lines, **required text** and required rule labels;
2. semantic dependencies;
3. optional plot, item and delta labels;
4. relation labels, then annotations;
5. decoration.

It also states: "A required label whose placement is a precondition for a route remains in phase 1."

In `rows.mode: lanes` every packed item's name, and its delta when selected, is **required**:
- the View must declare `overflow: visible-overflow`;
- acceptance row 2 forbids `W_LAYOUT_LABEL_SUPPRESSED` for a packed item;
- the lane allocator reserves the measured title and delta footprint, including any stagger level, in the lane's block extent before rows are final.

Lane-mode item labels are therefore **phase-1 required text**. They take their final position inside their own lane's reserved footprint, and they enter the single `SurfaceObstacleIndex` before dependencies are routed. Dependencies (phase 2) route around them under their unchanged bend, detour and overflow policy. A route that cannot be found is suppressed and diagnosed exactly as today, never hidden by moving a required name.

This is not the "labels veto routes" behaviour the #466 correction rejected. That rejection concerns *optional* labels. In `automatic` and `explicit` modes item labels stay optional and keep #466's phase 3.

The corrected lane closure is:
1. slots, scale, measured item footprints (marks plus title and delta text), group-local lane allocation, row extents, marks and ports, lane-local required names and deltas, and lane-table cells;
2. dependencies;
3. optional labels (none in lane mode);
4. relation labels and annotations;
5. decoration.

The lane label ladder (adjacent end, adjacent start, two staggered offsets) is evaluated in the lane-local frame against the lane's own reserved band. A lane name therefore never leaves its lane, which is the containment [#488](https://github.com/tya5/chrona/issues/488) asks for in automatic mode.

## 2. View version

View v0.23 is #428's as-of `date` form (landed `17e5e1a2`), and #426 takes v0.24. Lane rows take **the next free View version at landing**, currently expected to be v0.25. The schema is copied from the then-live View schema, so every earlier feature is preserved. The previous version becomes `transitioning` in the schema inventory. "v0.23" in the selected design and plan reads as "the lane View version".

## 3. Adjacent contracts landed since the design

- **#480 (row requirement from text).** The table cells a row holds are now part of `required_row_block_extents` through `text_line_block`. A lane row's requirement is `max(minBlockSize, lane footprint including stagger levels, lane-table cell line + paddingBlock)`. It is computed by the same function, so the Draft `auto` probe and placement agree.
- **#481 (group bands).** A group's band includes its own header row. Lane rows keep group-local packing, so a group's lanes are its rows under that band.
- **#487 (CSS-grid flex).** The lane table's `Lane` and optional `Items` columns are measured by `measure_table_columns`. A `minmax: {min: content}` table slot is never narrower than them.
- **#486 (attached milestones).** A milestone that `attachesTo` a task is placed on its host's lane by rule; #486 owns that attachment semantics and consumes this allocator.
- **#483 and #470 (defaults and presets).** "New Views and the packaged presets default to lanes" (acceptance row 5) migrates `default-draft.yaml` and the five catalogue presets to lane mode in the same corpus slice as the three slides.
- **Hierarchy:** HALCYON `06` stays `automatic`. The third committed lane slide is a non-hierarchy slide (`03` or `04`), as the selected design already said.

## 4. Unchanged

Use cases, the lane table grammar, lane identity, explicit `trackAllocation: collision`, measured footprints, the ≤12-lane and named-chain thresholds, and the Project, View, Layout and Scene ownership split are unchanged.
