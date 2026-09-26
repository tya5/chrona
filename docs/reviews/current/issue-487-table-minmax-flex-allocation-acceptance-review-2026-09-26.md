<!-- chrona:literal-acceptance/v1 -->

# Release Review — Table `minmax` Content Minimum and Flex Allocation (#487)

**Reviewed product:** `8f7ae47d` on the worktree branch (design amendment `d1cfab4c`,
implementation `8f7ae47d`). **Design:** [design](../../design/issue-487-table-minmax-flex-allocation-design-2026-09-26.md),
[architecture review](issue-487-table-minmax-flex-allocation-architecture-review-2026-09-26.md),
Specification 24 §2.1, Specification 33 §5, [ADR-0032](../../decisions/ADR-0032-flexible-track-minimum-is-a-floor.md).
**Slice review:** [I487-1](issue-487-table-minmax-flex-allocation-i487-1-review-2026-09-26.md).

**CI:** pending.

## Literal issue acceptance

### Issue #487

- Source: [Issue #487](https://github.com/tya5/chrona/issues/487)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `minmax: {min: content}` on a table slot is never narrower than its measured columns and gutters. | met | [I487-1 review](issue-487-table-minmax-flex-allocation-i487-1-review-2026-09-26.md): `layout/sources.py`'s table branch sets `minimum_inline` to the measured column+gutter extent (`_table_content_inline`); `test_content_sized_table_slot_is_its_measured_columns_and_gutters` and `test_table_column_floor_binds_when_the_measured_columns_are_narrower` in `tests/unit/chrona/presentation/layout/test_sources.py` assert it directly, and `_resolve_flexible_tracks`'s tests confirm the allocator never resolves a track below its minimum. | — |
| 2 | The flex-allocation meaning of a track minimum is specified (additive basis versus `max(min, share)`), and public evidence is migrated deliberately. | met | [I487-1 review](issue-487-table-minmax-flex-allocation-i487-1-review-2026-09-26.md): Specification 33 §5 and ADR-0032 specify CSS Grid's iterative "find the size of an fr" resolution (not a bare `max(min, share)`, which a same-day design amendment rejected for oversubscribing `available`); `tests/unit/chrona/presentation/layout/test_flexible_track_allocation.py` covers the min-exceeds-share, maximum-clamp, all-zero-minima and minima-exceed-available cases; the 18-slide public migration is measured, attributed per diagnostic, and visually inspected (three before/after PNG pairs) in the slice review. | — |

## Programme-level criteria (optional)

- The design's architecture review flagged one open question (does the lead accept most
  affected tables becoming narrower than today's published width): the lead approved,
  additionally requiring the flex-allocation algorithm correction recorded in the design
  amendment commit `d1cfab4c` before any code was written.
- Public evidence: 18 of 21 materializers changed, each attributed by table-width delta
  and diagnostic change in the [I487-1 review](issue-487-table-minmax-flex-allocation-i487-1-review-2026-09-26.md).
  No slide gained a new `W_LAYOUT_VISIBLE_OVERFLOW`.
- Focused tests: `tests/unit/chrona/presentation`, `tests/integration`, `tests/cli` — 771
  passed, 1 skipped. `conformance/run_conformance.py`: all 31 checks PASS.
- CI: pending — the lead fills in the run links once pushed.

## Architecture conclusion

Layout owns both contracts:
- `layout/sources.py::measure_sources`'s table branch reuses the #480 `_table_content_inline`
  measure for its minimum, so the slot and its columns cannot disagree in either direction.
- `layout/engine.py::_allocate` delegates to `_resolve_flexible_tracks`, one pure
  bases-to-sizes function used by every node kind and axis (Specification 33 §8); no
  table-specific allocator was introduced.

No Scene, adapter, schema, View, Theme, or metric-name change. `table.column.minInlineSize`
keeps its #480 meaning unchanged.

Release disposition: both literal rows are met, pending CI.
