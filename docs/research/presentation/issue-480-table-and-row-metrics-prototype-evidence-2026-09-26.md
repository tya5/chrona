# Prototype Evidence — Table and Row Metrics (#480)

This is evidence for the [#480 design plan](../../planning/active/issue-480-table-and-row-metrics-design-plan-2026-09-26.md), not a selected contract. It was collected from an unpublished, environment-gated prototype on `4e93dce4`. Baseline: all 21 public materializers reproduce; 640 focused tests pass and 1 is skipped (`tests/unit/chrona/presentation`, `tests/integration`).

## Candidates measured

| Candidate | Rule | Changed public outputs (of 21) | Warning changes | Focused tests |
| --- | --- | --- | --- | --- |
| A | table `preferred_inline` **and** `min_inline` from the measured columns (natural widths, hierarchy indent, gutters); `table.column.minInlineSize` unused | 18 SVG + Scene | new `W_LAYOUT_LABEL_SUPPRESSED`, `W_LAYOUT_NOTE_INDEX_SUPPRESSED` and relation-label suppressions where wider tables take room from the plot, legend and notes | 2 failures (a golden width for HALCYON `11-overlay-briefing`; an expected suppression count that disappears) |
| B | as A, but `preferred_inline = max(column_count × minInlineSize, measured)` | 18 SVG + Scene, the same numbers as A | as A | 0 failures |
| C | row requirement includes the table cell line block plus `paddingBlock`; the cell line box is centred in the row per its own role | 19 Scene + SVG, text baseline only (for example −3.375 px) | none | 0 failures |

## What drives the A/B churn

The growth is caused by `min_inline`, not by `preferred_inline`. Nine public layouts size the table as `minmax: {min: content, max: {fr: N}}`, and `layout/engine.py::_allocate` adds each flexible track's share of the remaining space **on top of** its minimum. It does not take CSS-grid `max(min, share)`. Today the table's `min_inline` is the widest row label. Raising it to the measured column sum therefore widens every such table by roughly the difference, for example HALCYON `01-mission-brief` 789.4 → 1059.5 px, and takes that space from the timeline.

This is a real, separate gap: `min: content` does not mean the table's content. Closing it changes the flex-allocation meaning of a content minimum across the corpus, and it is outside #480's literal criterion, which is about `inlineSize: content`. It needs its own issue and design.

In the corpus, the `minInlineSize` floor never binds when the measured sum is larger; the only content-only public slot (`11-overlay-briefing`, 3 × 210 = 630 px) is wider than its measured columns (383.8 px).

## Row candidate C

- No public warning set changes: every public Theme's rows are already taller than one cell line plus padding.
- Centring moves every table cell's text up by `size × (lineHeight − 1) / 2` within its unchanged row. This is 3.375–3.5 px for the public Themes.
- The prototype applied the text requirement only at placement. Draft `auto` block sizing (`timeline_content_block_requirement`) did not see it. With `print-mono`, 26 px rows and 6 px padding, rows therefore grew but the timeline did not: one `W_LAYOUT_ROW_DENSITY` and two `W_LAYOUT_MARK_OVERFLOW` appeared. The requirement must enter the one shared `required_row_block_extents` path used by both the probe and placement.

## Reproduction under the combined prototype

`print-mono` with a content-only table slot and 26/6 rows: 0 `W_LAYOUT_VISIBLE_OVERFLOW` (from 79). The remaining findings are the density and mark-overflow defects above, which come from the prototype's missing shared path.
