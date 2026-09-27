# I480-2 Review — Row Block From Its Text

**Implementation:** `12d4c670` on `main`. **Public base:** `537d0982` (the I480-1 review). **Design and plan:** [#480 design](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md), [implementation plan](../../planning/active/issue-480-table-and-row-metrics-implementation-plan-2026-09-26.md). This is a slice review; the issue acceptance review is separate.

## Evidence and byte review

- **Focused tests:** `.venv/bin/python -m pytest -q -n 6 tests/unit/chrona/presentation tests/integration tests/cli`, **719 passed**, 1 skipped.
- **Literal regression test:** `test_cli_row_height_is_derived_from_the_table_text_it_holds` copies `print-mono`, sets rows to 26 px with 6 px padding, and renders HALCYON-1 through the CLI.
  - On `537d0982` it fails. The same setup on `8c51fcb9` emitted 78 table-text `W_LAYOUT_VISIBLE_OVERFLOW` and 5 `W_SCENE_TEXT_INTERSECTION`.
  - On `12d4c670` it passes. Every row band is 27 px (21 px line + 6 px padding), and none of `W_LAYOUT_VISIBLE_OVERFLOW`, `W_SCENE_TEXT_INTERSECTION`, `W_LAYOUT_ROW_DENSITY` or `W_LAYOUT_MARK_OVERFLOW` appears. The last two cover the Draft `auto` probe, which the prototype had missed.
- **Unit tests:**
  - the row requirement is `max(minBlockSize, text line + padding, tracks + padding)` with padding added once;
  - the line block is the tallest cell role (`numeric` versus `text`) and 0 without cells;
  - a cell's line box is centred in its row.
- **Public materializers:** `--write`, then `--check`, reproduce 21 slides; 19 changed.
  - Structural comparison of every changed Scene: only `cell:*` primitives moved, plus the cell-attached icon `visual:cell:firmware:Workstream:leading` in Controller Z `icons` and `material-icons`, which follows its cell.
  - Every move is a pure block translation, with no inline, size, row, mark or diagnostic change: −2.6 to −2.8 px for Controller Z, ASTER and ORION, −3.0 to −3.5 px for HALCYON. This equals `size × (lineHeight − 1) / 2` for each Theme.
  - The two slides without table rows (`05-dependency-network`, `10-gallery-network-wallboard`) are unchanged.
- **Visual check:**
  - Before/after PNG crops of HALCYON `01-mission-brief` and Controller Z `executive` were rendered with resvg.
  - On Controller Z's striped rows, the old baseline sat visibly low in each band. The new text is centred against both the band and the bar in the same row.
  - No clipping or new collisions.
- **Generated reports** (`diagnostics/inventory.md`, `diagnostics/presentation-contrast.md`) changed only line numbers and cell coordinates.
- **Conformance and CI:** local PASS. [Four-job CI run 36243283266](https://github.com/tya5/chrona/actions/runs/36243283266) is green: Ubuntu, Windows and macOS conformance/full pytest/wheel, and newest-Python public materializer reproduction.

## Architecture review

`required_row_block_extents` is still the one row rule. It gained one input, `text_line_block`. `timeline_content_block_requirement` (the pre-layout probe) and composer placement pass the same value, computed by `table_text_line_block` from the same `TableContent.cells`. Draft `auto` extent and placement therefore cannot disagree.

`paddingBlock` keeps its existing total-padding meaning, now stated in Specification 24 §2.1. The cell baseline uses the cell's own role, not the body size. Plot labels, group headers, Scene and adapters are untouched. No Theme, View or schema file changed.

For #467, whose lane rows use the same function: the parameter defaults to 0, so a lane caller must pass the table line block to keep this guarantee. This is recorded in the #480 closing comment.

## Literal Issue #480 criterion disposition after this slice

| # | Literal acceptance criterion | State | Evidence / next unit |
| ---: | --- | --- | --- |
| 1 | A table slot at `inlineSize: content` is never narrower than the sum of its content-sized columns and gutters. A test covers the `print` Theme's `Δ` column. | met | [I480-1 review](issue-480-table-and-row-metrics-i480-1-review-2026-09-26.md). |
| 2 | A row metric can be expressed relative to the body text line, and Layout derives the block size. Or the Theme loader diagnoses a row height smaller than one text line plus padding. | met | `paddingBlock` is the row metric relative to the tallest table text line; Layout derives the block size; the tests and byte review above. |
