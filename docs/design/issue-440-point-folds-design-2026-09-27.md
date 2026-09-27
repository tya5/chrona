# Design — Milestone-Only Rows and Fold Policies (#440)

**Plan:** [design plan](../planning/active/issue-440-point-folds-design-plan-2026-09-27.md).

## 1. Group-header folds pack by collision (row 1)

The folded points of one group are packed with #467's `allocate_lanes`. The group key is the group id. Each candidate carries its mark footprint and its measured label width. Points whose marks and labels do not collide share a lane. The lanes stack inside the group header. The header grows only when the packed lanes exceed it, through the existing `W_LAYOUT_GROUP_HEADER_OVERFLOW` path. Index stacking is removed.

## 2. A folded point keeps its name and date (row 2)

Every point that leaves its own row is labelled with #486's required composition: title, planned date and finish delta. This covers points folded by `attached`, `predecessor`, `group-header` or `key-row`. The label is never suppressed. Where no candidate fits, it takes the terminal visible-overflow placement and is recorded as such. The facts the table row carried stay on the slide.

## 3. `points: key-row` (row 3)

- **View.** `rows.points: key-row` and an optional `rows.keyRow: {title: <text>}`, with default title `Key milestones`.
- **Projection.** Every selected point moves into one synthetic row placed first, directly under the axis. The row's table title cell shows the key-row title.
- **Layout.** The key row's points are packed with `allocate_lanes` under group key `key-row`. The row's block extent is the sum of its lanes. The row works with any grouping, including none.

## 4. Fallback lists

`rows.points` may be a list, for example `[predecessor, key-row]`. Each point is placed by the first policy that can place it, and `own-row` is the implicit last resort. A single value keeps its present meaning.

## 5. Corpus rule (row 4)

- **Measurement.** A corpus report computes the milestone-only row share of every committed slide. It extends `tools/corpus_coverage.py` with a "Milestone-only rows" section and a `--check` bound of 25%.
- **Reasons.** A View above the bound must declare `rows.points: own-row` with `rows.pointsReason: <text>`. The report prints that reason.
- **Slides.** They are moved to a fold or to lanes (#467) until each is within the bound or declares a reason.

## 6. Freed height (row 5)

The committed `key-row` slide uses `rowDistribution: fill` (#434), so rows taken out by the fold return their height to the remaining rows.

## Evidence

- **Row 1** is a test that renders `02-programme-board` with `points: group-header`. The committed `02` becomes a lanes slide under #467.
- **Rows 3 and 5**: `aster-ssd/overview` (75% milestone-only today) becomes the `key-row` slide, with `fill`.

## Boundaries

- **Projection** owns row membership.
- **Layout** reuses the one lane allocator, not a second packing algorithm.
- **Tooling** owns the corpus bound.
- There is no Scene or adapter change.
