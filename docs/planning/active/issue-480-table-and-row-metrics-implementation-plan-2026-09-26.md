# Implementation Plan — Table and Row Metrics (#480)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-480-table-and-row-metrics-architecture-review-2026-09-26.md). **Authority:** [design](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md), Specification 24 §2.1, [Issue #480](https://github.com/tya5/chrona/issues/480). The `min: content` flex question is [#487](https://github.com/tya5/chrona/issues/487) and is not implemented here.

## Literal acceptance ledger

1. “A table slot at `inlineSize: content` is never narrower than the sum of its content-sized columns and gutters. A test covers the `print` Theme's `Δ` column.”
2. “A row metric can be expressed relative to the body text line, and Layout derives the block size. Or the Theme loader diagnoses a row height smaller than one text line plus padding.”

## Coordination

The other dev session owns #466/#467/#478. #467 extends `required_row_block_extents`; slice I480-2 adds only the `text_line_block` parameter there, with a default of 0. Before each push, fetch `origin/main`, check ahead/behind and the staged file list, and stop on a conflict in `layout/presentation.py`, `layout/surface_composer.py` or `usecases/render_review.py`.

## I480-1: one table measure

**Owners/files:**
- `layout/presentation.py`: `measure_table_columns` and the indent helper; `place_table_columns` consumes them.
- `layout/sources.py`: `SourceInput.table`; the `table` branch uses the measure with the `minInlineSize` floor; `min_inline` unchanged.
- `review/v05_content.py`: extract `normalize_v05_table_content` and a module-level `cell_typography_role`.
- `usecases/render_review.py`: build the table content once before measurement and pass it to both consumers.
- `layout/surface_composer.py`: cell indent through the shared helper.

**Focused tests:**
- `print` Theme `Δ` column with a content-only slot through the CLI render path (no `W_LAYOUT_VISIBLE_OVERFLOW`, slot extent = measured sum);
- measure equals placement;
- the floor binds and surplus goes to the flexible column;
- the widest hierarchy cell at depth 2 includes its indent.

**Public evidence:** `tools.regenerate_public_examples --write` then `--check`. The expectation is no byte change except hierarchy-indent widening; attribute every change.

**Gate:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`), conformance, 21 materializers, then push and the four-job CI. The slice review is published separately.

## I480-2: row block from its text

**Owners/files:**
- `layout/presentation.py`: `required_row_block_extents(text_line_block=…)`.
- `layout/surface_composer.py`: both call sites (`timeline_content_block_requirement` and placement) and the centred cell baseline using the cell's role.
- `usecases/render_review.py`: passes the same line block to the probe, computed from the View's table columns through `cell_typography_role`.
- One Layout helper computes the line block from the Theme and roles.

**Focused tests:**
- a 26/6 `print` row becomes 27 px, with no table-text overflow and no `W_SCENE_TEXT_INTERSECTION` (CLI render of the copied preset);
- a `numeric` role taller than `text` sets the requirement;
- the Draft `auto` extent equals the placed rows;
- the cell box is centred;
- no table columns means no text requirement.

**Public evidence:** a batch of all 21. The expected change is table cell text `y`/baseline only, on the table slides. Inspect before/after PNGs of HALCYON `01-mission-brief` and Controller Z `executive`.

**Gate:** as I480-1.

## I480-3: issue acceptance

This is a separate acceptance review under `docs/reviews/current/`, with a row per literal criterion, test links, CLI output for both reproductions, the batch diffs, and the green CI run. Close #480 only then.

If a slice exposes a row whose Theme is already smaller than its text, a table width change not explained by the indent, or a conflict with #467's row path, pause, publish a design correction, and amend this plan.
