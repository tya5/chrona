# I480-1 Review — One Table Measure

**Implementation:** `5eca7b3a` on `main`. **Public base:** `14b05b25` (the #480 implementation plan). **Design and plan:** [#480 design](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md), [implementation plan](../../planning/active/issue-480-table-and-row-metrics-implementation-plan-2026-09-26.md). This is a slice review; Issue #480 remains open for I480-2 and final acceptance.

## Evidence and byte review

- **Focused tests:** `.venv/bin/python -m pytest -q -n 6 tests/unit/chrona/presentation tests/integration tests/cli`, **715 passed**, 1 skipped.
- **Literal regression test:** `test_cli_content_sized_table_slot_holds_the_print_theme_delta_column` copies `print-mono`, sets the table slot to `inlineSize: content`, and renders HALCYON-1 through the CLI. It fails on `14b05b25`, where `column:Δ` crosses the table edge, and passes on `5eca7b3a`. The CLI reports no `W_LAYOUT_VISIBLE_OVERFLOW`.
- **Unit tests:**
  - the slot's preferred extent equals `place_table_columns`' placed extent;
  - the `minInlineSize` floor binds when the columns are narrower;
  - `min_inline` keeps its floor-and-label basis (#487);
  - a depth-2 hierarchy cell's indent is part of its column's natural width.
- **Public materializers:** `tools.regenerate_public_examples --write`, then `--check`, reproduce 21 slides. Only two changed; both are attributed below. No diagnostic changed.
  - `halcyon-1/07-replan-baseline`: the hierarchy column (`Work package`, `minmax: {min: content, max: {fr: 1}}`) grows by its widest cell's indent, 5.967 px. The following columns and their cells move right by the same amount (21 primitives). This is the intended hierarchy-indent correction.
  - `halcyon-1/06-flight-readiness`: its hierarchy column is `fill`, so the indent is absorbed by the flexible share. Only a 1e-13 float residue in one primitive's width changes (Scene only; SVG identical).
- **Generated reports:** `docs/diagnostics/inventory.md` changed only line numbers. `docs/diagnostics/presentation-contrast.md` changed only the moved 07 cell coordinates.
- **Conformance and CI:** local `run_conformance.py` PASS. [Four-job CI run 36242988538](https://github.com/tya5/chrona/actions/runs/36242988538) is green: Ubuntu, Windows and macOS conformance/full pytest/wheel, and newest-Python public materializer reproduction.
- **A problem found and corrected before publication:** the first build also raised the table's `min_inline`, because `min(preferred, widest label)` depended on the new preferred extent. That widened eight Controller Z/ASTER tables, by up to 54 px, and added a note-index suppression. It contradicted the design ("`min_inline` is unchanged"), so `min_inline` was pinned to its existing floor-and-label basis before commit; #487 owns it.

## Architecture review

`measure_table_columns` in `layout/presentation.py` is now the only natural-width rule. `place_table_columns` calls it, and `measure_sources` calls it through `_table_content_inline`. The shared `table_text_measurer` and `table_cell_indent` replace the composer's local copies, so measurement and placement cannot diverge in role metrics, numeric spacing or indent.

`normalize_v05_table_content` builds typed table facts once in the use case. The same `TableContent` object feeds measurement (`SourceInput.table`) and surface content. The use case measures nothing. No Scene, adapter, schema, View or Theme file changed.

## Literal Issue #480 criterion disposition after this slice

| # | Literal acceptance criterion | State | Evidence / next unit |
| ---: | --- | --- | --- |
| 1 | A table slot at `inlineSize: content` is never narrower than the sum of its content-sized columns and gutters. A test covers the `print` Theme's `Δ` column. | met | `preferred_inline = max(floor, measured columns + gutters)` from the placement measure; the `print` `Δ` CLI test and unit equality test above. |
| 2 | A row metric can be expressed relative to the body text line, and Layout derives the block size. Or the Theme loader diagnoses a row height smaller than one text line plus padding. | not met | I480-2. |

I480-1 is accepted. The next public base is this review's commit; I480-2 may be published.
