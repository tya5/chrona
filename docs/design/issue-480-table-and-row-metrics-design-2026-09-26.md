# Design — Table and Row Metrics (#480)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-480-table-and-row-metrics-design-plan-2026-09-26.md). **Evidence:** [prototype evidence](../research/presentation/issue-480-table-and-row-metrics-prototype-evidence-2026-09-26.md). **Authorities:** Specifications 07 §5.1, 24 §2, 33, 38 §3, 43; the [#403/#404 table allocation correction](issues-404-403-table-allocation-closure-correction-2026-09-25.md).

## Use cases

1. An author sizes the table slot by its content (`inlineSize: content`). The slot is exactly as wide as its measured columns and gutters, and never narrower. No column crosses the table edge because two computations disagree.
2. An author chooses row density once. A row is always tall enough for one line of the table text it holds plus the declared padding, and nobody computes `fontSize × lineHeight` by hand.

## Contract 1: one table measure

**Owner: Layout.** `layout/presentation.py` gains one pure function, `measure_table_columns`. It returns each column's natural width and content minimum from the typed columns, cells, per-row indents, text measurer, inset and gutter. `place_table_columns` uses its result instead of its own inline computation. `measure_sources` also calls it for the `table` source. There is no second width rule.

- **Natural column width** = `max(inset, widest measured text + inset)`, where the inset is the body size, as today. Measured text is the header in its orientation and every cell in its own typography role.
- **Hierarchy indent** is part of the measured text extent. For the column named by `table_hierarchy_column`, a cell's extent is its text plus the indent of its row: `body_size` for a grouped row plus `table.indent.inlineSize × depth`. The indent rule moves into one Layout helper, used by measurement and by cell placement. Today placement subtracts the indent from an allocation that never included it.
- **Table content extent** = the sum of natural widths + `gutter × (columns − 1)`.
- **Slot measurement:**
  - `preferred_inline = max(column_count × table.column.minInlineSize, table content extent)`.
  - The metric keeps its existing meaning as a per-column floor for a content-sized table slot. It is not a column minimum.
  - Surplus above the content extent goes to flexible columns (`fill`/`fr`), as `place_table_columns` already does.
  - This keeps every public Theme and output unchanged where the floor already binds. The metric is not retired, so no Theme migration is needed.
- **`min_inline` is unchanged** (the widest row label). Making `minmax: {min: content}` mean the table content changes the additive flex allocation on 18 public slides (see the evidence). It is filed as [#487](https://github.com/tya5/chrona/issues/487) and is not part of this contract.

**Ingress.** Measurement runs before `solve_layout`, but the typed table content is currently normalized after it, inside `normalize_v05_surface_content`. Only its detail-profile part needs the Layout manifest. The table part becomes one function, `normalize_v05_table_content(projection, project, view, actual_set, locale)`, returning columns, cells and hierarchy column. The use case calls it once, before measurement. It passes the result to `SourceInput.table` for measurement and to `normalize_v05_surface_content` for surface content, so the table is built once and the cells are identical in both. The use case does not measure. Row indents come from the projection rows (`group_id`, `depth`), which measurement and placement read in the same way.

## Contract 2: row block from its text

**Owner: Layout.** `required_row_block_extents` gains `text_line_block`. Each row's requirement is:

```
max(timeline.row.minBlockSize,
    mark-track extent + timeline.row.paddingBlock,
    text_line_block + timeline.row.paddingBlock)
```

- `text_line_block` is the largest `fontSize × lineHeight` among the typography roles of the table cells. Today these are `text` and, for a `signedDays` column, `numeric`. It is 0 when the View has no table columns.
- The role choice (`cell_typography_role`) becomes one named function, shared by content normalization and the pre-layout probe.
- **`paddingBlock` is the total block padding of a row**: the extent added once to the row's content. This is the existing code behavior, now stated. It is not per side.
- `minBlockSize` remains a floor. Density becomes one choice: an author who wants "one text line plus padding" sets padding and leaves the floor below the line.
- **One path.** The pre-layout probe (`timeline_content_block_requirement`, used for Draft `auto` and profile growth) and row placement both call `required_row_block_extents` with the same `text_line_block`. The prototype showed that a placement-only rule produces `W_LAYOUT_ROW_DENSITY` and mark overflow. #467's lane requirement extends this same function; this change adds one parameter and no second path.
- **Cell placement.** A table cell's line box is centred in its row, using the cell's own role. The line box top is `row.block + (row.blockSize − L) / 2`, with `L = size × lineHeight`, and the baseline is `top + size`, following the existing `place_text` box convention. This replaces `row centre + body_size / 2`, which ignored line height and the cell's role.
- The fit check is unchanged: a cell whose box leaves its row is still `W_LAYOUT_VISIBLE_OVERFLOW`. After this change, that can happen only for a larger declared role or font fallback, never for a row the requirement closed.

**Out of scope:** plot labels are not row-held text. They search the plot slot with obstacles, and #466 owns that model. Group header text is placed in its header band and is unchanged.

## Why not diagnose at Theme load

The issue offers a loader diagnostic as an alternative. The Theme does not know which cell roles a View will use (`numeric` only with a `signedDays` column), and a diagnostic would still leave the arithmetic to the author. Deriving the row in Layout meets the first alternative literally, and the row metric `paddingBlock` is expressed relative to the text line.

## Migration and compatibility

- No schema, View, Theme syntax or metric-name change, and no Theme file changes.
- Specification 24 gains §2.1, stating the table measure, the metric's meaning, `paddingBlock` and the row requirement.
- **Public evidence:**
  - Contract 1 is expected to change no public byte (the floor binds everywhere in the corpus).
  - The hierarchy-indent inclusion may widen a hierarchy column where a grouped or deep row's cell was the widest. This is verified by the batch.
  - Contract 2 moves table cell text up by `size × (lineHeight − 1) / 2` on the 19 table slides, with no geometry or warning change.
  - All 21 materializers are regenerated in one batch per slice, and representative images are inspected.

## Diagnostics

No new diagnostic. A too-small row no longer produces `W_LAYOUT_VISIBLE_OVERFLOW`, because Layout closes it. An overflow that remains is still reported by the existing fit check.

## Tests

- The `print` Theme's `Δ` column with a content-only table slot: no overflow, and the slot extent equals the measured sum.
- The measure equals the placement: the sum of `place_table_columns` widths equals `preferred_inline` when the floor is lower.
- The floor binds and surplus goes to the flexible column.
- Hierarchy indent: a depth-2 cell that is the widest widens its column by its indent.
- A 26/6 `print` row becomes 27 px, with no table-text overflow and no `W_SCENE_TEXT_INTERSECTION`.
- A `numeric` cell with a larger line block than `text` sets the requirement.
- The Draft `auto` extent equals the sum of placed rows.
- A cell line box is centred, with its own role.
