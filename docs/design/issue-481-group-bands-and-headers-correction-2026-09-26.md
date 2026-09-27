# Design Correction — Group Band/Header Translucent Overlap (#481)

**Status:** accepted correction to the approved [#481 design](issue-481-group-bands-and-headers-design-2026-09-26.md), found while implementing Contract 2. **Trigger:** `tests/unit/chrona/presentation/scene/test_v05_builder.py::test_grouped_rows_reserve_and_emit_a_group_header` and `::test_header_fold_projects_mark_label_route_and_annotation_without_a_point_table_row` began raising `E_LAYOUT_BACKGROUND_OVERLAP` once `GroupPlacement.content_bounds` folded in the header block.

## Finding

`_validate_background_shapes` rejects any two translucent (`backgroundTreatment: fill`, `opacity < 1`) background shapes whose bounds intersect, regardless of which roles they belong to. Before Contract 2, a group's `groupBand` (`content_bounds`) and its own `groupHeaderBand` (`header_bounds`) never overlapped — `content_bounds` started only after the header block. Contract 2 makes `content_bounds` include the header block by design, so a group's own `groupBand` and `groupHeaderBand` shapes now legitimately share the header row's block extent whenever their Layout Profile `backgroundExtents` give them any overlapping inline range (for example `groupBand: timeline` and `groupHeaderBand: both`, both inline-overlapping in the timeline). If both roles are declared translucent, the validator now raises `E_LAYOUT_BACKGROUND_OVERLAP` for a same-group pairing that is not a conflict: it is one group's two intentional decoration layers (body tint, header accent) sharing the header row on purpose.

No shipped preset is affected — all five bind `group-band` and `group-header-band` opacity to `1` (opaque), so the check never triggered a false positive there. The unit-test fixture (`tests/unit/chrona/presentation/scene/test_v05_builder.py`) uses translucent test values (`0.12`, `0.2`) for both roles and surfaced the gap.

## Correction

`_validate_background_shapes` exempts exactly a `groupBand`/`groupHeaderBand` pair that shares the same `source_ref` (the same `group_id`) from the intersection check — they are one group's own layered decoration, not two independent decorations. Every other pairing (two different groups, a group band and a row stripe, a group band and the calendar-closed band, etc.) is still checked exactly as before; the check still rejects a genuine translucent conflict.

## Why not relax the check generally

The check exists to keep an author from compounding two *unrelated* translucent fills into an unreadable double-tint. A group's header row sharing its own body band's tint is not that case — it is the literal contract of #481's Contract 2 ("a group's band includes its own header row"). Narrowing the exemption to the same `group_id` and exactly this role pair keeps the check's original protection for every other combination.

## Verification

Both previously-failing unit tests pass with the correction; the full focused suite (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`) is green. No new test is added for the exemption itself beyond the two pre-existing tests it unblocks, since they already exercise a translucent `groupBand`/`groupHeaderBand` pair through the public `compose_review_surface` entry point.
