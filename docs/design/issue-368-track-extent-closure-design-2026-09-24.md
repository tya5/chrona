# Issue 368: completed track extent closure design

## Root cause

`place_rows` assigns one uniform height to every review row. The previous
content requirement summed per-row lane counts instead of multiplying the
largest required row extent by the row count. A multi-lane/multi-milestone row
therefore could fit the aggregate estimate yet receive too little individual
height. Separately, the estimate duplicated a `3 * markSize` placement rule.

## Decision

The existing completed track planner is the sole containment authority. Layout
adds a planner-owned `minimum_track_block_extent(row, mark_size)` query that
uses the same placement and containment checks as final track placement. It
finds the smallest finite row block that produces no `E_LAYOUT_MARK_OVERFLOW`.

For uniform row allocation, the timeline requirement is:

`rowCount * max(themeRowMinimum, eachRowTrackMinimum) + groupHeaderExtent`

The pre-layout auto extent resolver and final surface composer consume this
same requirement. Fixed viewports reject before Scene with an actionable
required/available diagnostic. Scene remains only a projection consumer.

## Architecture review

This removes duplicated policy from `surface_composer`; `presentation.py` owns
track geometry and its minimum extent, while `surface_composer` combines named
Layout allocations. No Theme mutation, mark shrinking, renderer policy, or
Context adaptation is introduced.
