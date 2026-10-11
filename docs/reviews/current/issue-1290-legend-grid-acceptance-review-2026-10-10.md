<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — legend grid columns and a start-column slot caption (#1290)

Implementation: [#1335](https://github.com/tya5/chrona/pull/1335) (merge `b982d583`), checked against `origin/main` `289444de`. A legend slot may declare `columns` (integer of at least 1): entries fill the columns in reading order (entry k in column k mod `columns`), each column as wide as its widest entry, `gap` apart; `direction` and `itemMinInlineSize` are then not used, and the grid is measured exactly so the slot is allocated its true block. A slot heading may take `block: start-column`: the caption holds the inline-start column of a legend slot that declares `columns`, inside the entries' block extent; on any other slot it falls back to `top` with `I_LAYOUT_SLOT_HEADING_NO_START_COLUMN:<node>`. `layout-profile-v0.10` gains `columns` in place and widens the caption `block` enum (five expected-delta lines). Specification 33 states both. Plan: [Status comment](https://github.com/tya5/chrona/issues/1290).

## Literal issue acceptance

### Issue #1290

- Source: [Issue #1290](https://github.com/tya5/chrona/issues/1290) (body, assignment and Status comments)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `columns: n`, entries occupy `ceil(count / n)` rows, entry `k` in column `k mod n` or row-major per the declared order, Scene-checkable from the swatch and label bounds. | met | [`test_legend_grid.py`](../../../tests/integration/test_legend_grid.py) `test_entries_fill_ceil_count_over_columns_rows_in_reading_order` (four entries, 3 columns: two label rows, entries 0 to 2 on one row with increasing swatch inline starts, entry 3 on the next row in column 0), `test_each_column_is_as_wide_as_its_widest_entry` (2 columns, entries 1 and 3 share a column start past the widest label of column 0), `test_a_single_column_stacks_every_entry` and `test_a_grid_that_does_not_fit_its_slot_reports_the_track_overflow` (the slot is allocated its measured rows). All read swatch and label bounds from the completed surface. Specification 33 section on the legend slot states the rule. | — |
| 2 | With `block: start-column` the heading's block extent is within the entries' block extent and its inline extent does not overlap an entry. | met | `test_a_start_column_heading_sits_beside_the_entries_within_their_block_extent` in the [same file](../../../tests/integration/test_legend_grid.py) (heading top and bottom within the entries' top and bottom; every swatch starts at or after the heading's inline end), and `test_a_start_column_heading_on_a_legend_without_columns_falls_back_to_the_top_with_a_record` (`I_LAYOUT_SLOT_HEADING_NO_START_COLUMN`). Code: `layout/slot_heading.py`, `layout/surface_composer.py` (inline reserve), `layout/sources.py`; schema `schemas/layout-profile-v0.10.schema.yaml`. | — |
| 3 | Absent properties are byte-identical. Synthetic fixture test. | met | Synthetic Project and Layout Profile built in the [test file](../../../tests/integration/test_legend_grid.py) (no `examples/**` read). Absent properties: `test_without_columns_the_legend_is_unchanged` compares a legend without `columns` to an explicit `direction: block`, which is a weak check on its own; the stronger evidence is the [PR count table](https://github.com/tya5/chrona/pull/1335): all 46 slides rendered on the base and on the head were byte-identical in SVG and Scene JSON, and no Theme or Layout Profile in the corpus declares `columns` or a `start-column` caption (search on `289444de`). All seven tests pass on `289444de`. | — |
| 4 | Do not edit `examples/**`. | met | [Diff](https://github.com/tya5/chrona/pull/1335/files): schema, the expected-delta file, Spec 33, `layout/` sources, `usecases/render_review.py` and the test; no `examples/**` and no bot-generated file. | — |
| 5 | The reviewer adopts it in slide 25. | deferred | Reviewer step, not a developer closing condition: the [Sunday Strip Layout Profile](../../../examples/halcyon-1/layouts) does not yet declare `columns` or a `start-column` heading (search on `289444de`). Owner note: adoption is the reviewer's YAML change in slide 25 and needs no code here. | [#1269](https://github.com/tya5/chrona/issues/1269): assemble the Sunday Strip target; adoption of the key panel in slide 25. |

## Programme-level criteria (optional)

None. Rows 1 to 4 are met; row 5 is the reviewer's adoption step on #1269. The issue can close after this review and the three-OS run on the `main` commit that publishes it are cited, unless the owner wants adoption confirmed first.
