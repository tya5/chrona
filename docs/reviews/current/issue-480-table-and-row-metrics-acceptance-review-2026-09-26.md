<!-- chrona:literal-acceptance/v1 -->

# Release Review — Table and Row Metrics (#480)

**Reviewed product:** `12d4c670` on `main` (I480-1 `5eca7b3a`, I480-2 `12d4c670`). **Design:** [design](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md), [architecture review](issue-480-table-and-row-metrics-architecture-review-2026-09-26.md), Specification 24 §2.1. **Slice reviews:** [I480-1](issue-480-table-and-row-metrics-i480-1-review-2026-09-26.md), [I480-2](issue-480-table-and-row-metrics-i480-2-review-2026-09-26.md).

## Literal issue acceptance

### Issue #480

- Source: [Issue #480](https://github.com/tya5/chrona/issues/480)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A table slot at `inlineSize: content` is never narrower than the sum of its content-sized columns and gutters. A test covers the `print` Theme's `Δ` column. | met | [I480-1 review](issue-480-table-and-row-metrics-i480-1-review-2026-09-26.md): one Layout measure for slot and columns; `test_cli_content_sized_table_slot_holds_the_print_theme_delta_column` fails before and passes after. | — |
| 2 | A row metric can be expressed relative to the body text line, and Layout derives the block size. Or the Theme loader diagnoses a row height smaller than one text line plus padding. | met | [I480-2 review](issue-480-table-and-row-metrics-i480-2-review-2026-09-26.md): row = max(floor, tallest table text line + `paddingBlock`, tracks + `paddingBlock`) on the shared probe/placement path; `test_cli_row_height_is_derived_from_the_table_text_it_holds` fails before and passes after. | — |

## Programme-level criteria (optional)

- The reproduction from the issue is closed end to end through the CLI.
  - The `print-mono` content-only table: 0 overflows (from 1).
  - The 26/6 rows: 0 table-text overflows and 0 text intersections (from 78 and 5).
- CI: [run 36242988538](https://github.com/tya5/chrona/actions/runs/36242988538) (I480-1) and [run 36243283266](https://github.com/tya5/chrona/actions/runs/36243283266) (I480-2) are green on all four jobs: three-OS conformance/full pytest/wheel, and newest-Python public materializer reproduction.
- Public evidence changed only as attributed in the slice reviews:
  - the hierarchy indent in HALCYON 07;
  - cell text centring on the 19 table slides.

## Architecture conclusion

Layout owns both rules:
- `measure_table_columns` is the single table width measure;
- `required_row_block_extents` is the single row rule, shared by the Draft `auto` probe and placement.

The use case only normalizes typed table content once, before measurement. No Scene, adapter, schema, View, Theme or metric-name change.

Out of scope, and not left silent: `minmax: {min: content}` and additive flex allocation are [#487](https://github.com/tya5/chrona/issues/487). #467 lane rows must pass `text_line_block` when they extend the row rule.

Release disposition: both literal rows are met.
