# Design Plan — Table and Row Metrics (#480)

**Public base:** `8c51fcb9` on `main`. **Source of truth:** [Issue #480](https://github.com/tya5/chrona/issues/480), Specifications 07 (§5.1 metrics), 24, 33 (intent-oriented layout), 38 (review rows), 43 (typography-aware source measurement) and 50, and the [#403/#404 table allocation correction](../../design/issues-404-403-table-allocation-closure-correction-2026-09-25.md). **Related:** #470 (the `print-mono` tuning that found both defects), #467 (lane rows; it also changes the row requirement path and is owned by the other dev session).

## Published baseline, inference, and unverified facts

Reproduced on `8c51fcb9` with a copied `print-mono` preset and HALCYON-1 (`--actual`):

1. **Content-sized table.** With the table slot at `inlineSize: content`, the CLI reports `W_LAYOUT_VISIBLE_OVERFLOW` on `column:Δ` (`availableInline: 45.55`, `requiredInline: 46.634`). Cause, published code:
   - `layout/sources.py::measure_sources` measures the `table` source as `preferred_inline = column_count × table.column.minInlineSize` (3 × 130 = 390) and `min_inline = min(preferred, widest row label)`. It never sees the table's columns or cells.
   - `layout/presentation.py::place_table_columns` measures each column's header and cells (natural width = widest text + body-size inset) and adds gutters: 391.08 here. Under `visible-overflow` it keeps natural widths, so the last column crosses the slot edge.
   - The slot measure and the column measure are two unrelated computations. `mission-light` escapes only because its measured columns happen to sum below `3 × 130`.
   - Inferred, **not yet proved**: `minmax: {min: content, …}` (used by nine public layouts) has the same gap; its minimum is the widest row label, not the columns. It is hidden while the `fr` share is large enough.
   - Found while tracing, same defect class: the hierarchy column's indent (`body_size` for grouped rows plus `table.indent.inlineSize × depth`, `surface_composer.py`) is subtracted from the cell allocation but is not part of the column's natural width. A deep hierarchy therefore overflows even a correctly measured column.
2. **Row height ignores text.** With `timeline-row-height: 26` and `timeline-row-padding: 6`, the render emits 78 `W_LAYOUT_VISIBLE_OVERFLOW` (`table-text`) and 5 `W_SCENE_TEXT_INTERSECTION`. Cause, published code:
   - `required_row_block_extents` closes each row as `max(minBlockSize, mark-track extent + paddingBlock)`. Table text is not an input.
   - A table cell's baseline is `row centre + body_size / 2`, and `place_text` bounds are `[baseline − size, + size × lineHeight]`. The 21 px line box (14 × 1.5) therefore sits 3.5 px below centre and crosses a 26 px row by 1 px, although it is shorter than the row.
   - The baseline formula uses the body size even for `numeric` cells, and does not use the measured baseline that Specification 43 requires for Layout-placed text.
   - The issue's arithmetic (14 × 1.5 + 2 × 6 = 33) reads `paddingBlock` as per-side. The code applies it once in total to the mark stack. This contract has to be stated, not assumed.
3. Unverified until prototype evidence: which of the 21 public materializers change under each candidate rule, and by how much.

## Literal issue acceptance ledger

1. “A table slot at `inlineSize: content` is never narrower than the sum of its content-sized columns and gutters. A test covers the `print` Theme's `Δ` column.”
2. “A row metric can be expressed relative to the body text line, and Layout derives the block size. Or the Theme loader diagnoses a row height smaller than one text line plus padding.”

## Use cases and decisions to close

1. **Table content measure.** An author sizes the table slot by its content and gets exactly the columns' width. Decide:
   - one Layout-owned table measurement used by both source measurement and column placement, including gutters and hierarchy indent;
   - how table columns/cells reach measurement, which today runs before surface-content normalization;
   - `min_inline` for `minmax: {min: content}`: content-column natural widths, and the ellipsis floor for flexible columns only under `ellipsize-with-source`;
   - the future of `table.column.minInlineSize`: retire it, make it a per-column floor, or keep it as a slot-level floor. Each has a different byte impact on public evidence.
2. **Row block from its text.** An author chooses density once and never does line-height arithmetic. Decide between the issue's two options:
   - Layout derives the row requirement from the table text it holds;
   - the Theme loader diagnoses a too-small row.

   The loader cannot know which typography roles a row will hold, because that depends on View columns (`numeric` versus `text`). Layout derivation is the preferred direction, pending review. Also decide:
   - the `paddingBlock` meaning (total or per side);
   - vertical placement of cell text (a centred line box; Specification 43's measured baseline);
   - whether plot labels count as row-held text. Current evidence says no: plot labels search the slot with obstacles and are not row-contained. #466 owns that model.

## Responsibility and architecture review questions

- Layout owns measurement, allocation and placement (Specifications 33, 43; the #403/#404 correction). Can the table measure live in `layout/presentation.py` next to `place_table_columns` and be called from `measure_sources`, with the use case supplying typed table content earlier, without the use case measuring anything?
- Does moving table-content normalization before `solve_layout` break any dependency on the Layout manifest? Only the detail profile currently uses the manifest.
- Does a row requirement from text conflict with #467's lane requirement? Both must extend the one `required_row_block_extents` function, not add a second path. The change is kept to one additive input so #467 can rebase.
- Does Specification 07's metric vocabulary change (retired or redefined metric)? If so, add a Specification 07/24 amendment, and state the Theme migration for all 14 public Themes that bind the metric.
- Draft `auto` block extent (`timeline_content_block_requirement`) must use the same row requirement as placement, so it cannot drift.

## Ordered design slices and acceptance evidence

1. **D480-1: prototype evidence.** Measure the byte and warning impact on all 21 public materializers for: pure measured table content; measured content with a `minInlineSize` slot floor; the row text requirement with a centred line box. Publish the findings as research evidence.
2. **D480-2: contract.** Choose the table measure and the metric disposition, the row text requirement, the `paddingBlock` meaning and the cell baseline. Update Specifications 07/24/38 as needed and publish `docs/design/issue-480-table-and-row-metrics-design-2026-09-26.md`.
3. **D480-3: whole-architecture review.** Check the contract against Layout ownership, the #467 row path, draft `auto` extents, the Theme metric vocabulary and public evidence. Publish it under `docs/reviews/current/`.
4. **D480-4: implementation plan.** Expected slices: table measure (item 1), row text requirement (item 2), public evidence regeneration. For each, name owners, focused tests (the `print` Theme `Δ` column; a 26/6 row; numeric cells; hierarchy indent), and a 21-materializer batch diff.

Issue acceptance needs a separate review with one row per literal criterion, direct test and rendered-output evidence, the batch materializer diff, and the green four-job CI.
