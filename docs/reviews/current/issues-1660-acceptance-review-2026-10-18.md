<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #1660

Observed on `main` at `ed5525405`, which contains [PR #1670](https://github.com/tya5/chrona/pull/1670) (merge `be89bcd5d`) and its derived-sync bot commit `e71c8de3d`. The criteria are copied from the #1660 body re-fetched on 2026-10-18 (`gh issue view 1660`): three bullets, two of them compound, split here into eight rows. Tests were run on this base with a private `PYTHONPATH` (no install into a shared environment): `pytest tests/integration/test_all_point_group_header_1660.py` 8 passed; the existing group-header, folded-point, lane, key-row, hosted-point and explicit-row suites (`test_folded_point_lanes`, `test_group_header_baseline`, `test_folded_deadline_marks`, `test_group_header_strip`, `test_key_row`, `test_hosted_points`, `test_lane_theme_handoff`, `test_explicit_window_render`: 81 passed; `test_chip_box_follows_text`, `test_filled_annotation_heading`, `test_forecast_occurrence_coverage`, `test_forecast_label_ownership`, `test_actual_variance_paint`, `test_semantic_field_roles`: 59 passed). The issue's reproduction was rendered here with `chrona render ... --format png` and `--format svg`; the PNG was opened and inspected.

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #1660 | [#1670](https://github.com/tya5/chrona/pull/1670) (`ReviewProjection.rows_resolved` / `has_rows` / `group_order`; Layout places header-only group containers) | none |

## Literal issue acceptance

### Issue #1660

- Source: [Issue #1660](https://github.com/tya5/chrona/issues/1660)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic all-point group-header View has only its declared folded occurrences: no resurrected ordinary rows/marks/table labels. | met | [`test_all_point_twin_has_only_the_folded_occurrences`](../../../tests/integration/test_all_point_group_header_1660.py) asserts planned ids are exactly `planned:group-header:a:one` and `planned:group-header:a:two`, `surface.rows == ()` and one group `a` with its "Team a" header (provenance: `test_folded_occurrences_keep_project_provenance`). The issue repro was rendered here: planned primitives are those two only. In the rendered SVG the only scene ids are `group:a`, axis items, `title`, `group-header:a`, the two folded `planned:group-header:a:*` marks and their `member-label:group-header:a:*` labels, so no ordinary-row mark and no per-row table label exists. Caveat: the test asserts rows and planned marks, not a table-label list; the label absence is shown by the SVG scene ids above and follows from the empty row set. | — |
| 2 | Mixed groups and multiple groups retain their declared order and header containers. | met | [`test_groups_without_ordinary_rows_keep_declared_order_beside_mixed_groups`](../../../tests/integration/test_all_point_group_header_1660.py): groups come out `a, c, b, d` (mixed `a`, `c`; point-only `b`, `d`), rows are `s1, s3`, header blocks ascend and every group has header bounds. [`test_a_leading_point_only_group_precedes_a_mixed_group`](../../../tests/integration/test_all_point_group_header_1660.py) gives `b, a` for a leading point-only group. | — |
| 3 | Distinguish absent/legacy row inputs from a resolved empty View row set structurally. | met | [`ReviewProjection.rows_resolved` and `has_rows`](../../../src/chrona/presentation/model/projection.py) (field and property; View composition sets `rows_resolved=True`). [`test_projection_distinguishes_resolved_empty_rows_from_absent_rows`](../../../tests/integration/test_all_point_group_header_1660.py): a legacy projection has `has_rows` false, the same projection with `rows_resolved` has `has_rows` true and `rows == ()`. Rule in [Spec 38](../../specification/38-review-row-composition.md), paragraph "Group-header points and an empty ordinary row set (#1660)". | — |
| 4 | Layout does not redo View membership. | met | Layout reads `projection.has_rows` instead of an empty-tuple test in [`surface_base.py`](../../../src/chrona/presentation/layout/surface_base.py), [`surface_preparation.py`](../../../src/chrona/presentation/layout/surface_preparation.py), [`point_hosting.py`](../../../src/chrona/presentation/layout/point_hosting.py), [`surface_mark_visibility.py`](../../../src/chrona/presentation/layout/surface_mark_visibility.py) and [`surface_routes.py`](../../../src/chrona/presentation/layout/surface_routes.py); items are rebuilt into rows only for a projection with no rows marker. Header-only containers come from the View's declared `group_order` through [`empty_group_slots`](../../../src/chrona/presentation/layout/presentation.py). Evidence is code reading plus the repro: no row is derived from `projection.items` for a resolved projection. | — |
| 5 | Cover group containers with no ordinary rows, labels, routes and source provenance. | met | Container, label and order: row 1 and row 2 tests ("Team a" header in the all-point test; header bounds on every group in the multi-group test). Routes: [`test_folded_points_keep_their_routes`](../../../tests/integration/test_all_point_group_header_1660.py) requires the folded dependency routes to be non-empty and equal to those of a twin that keeps a span row. Provenance: [`test_folded_occurrences_keep_project_provenance`](../../../tests/integration/test_all_point_group_header_1660.py) maps each folded occurrence to its Project object (`one`, `two`). | — |
| 6 | Existing mixed plans, explicit/lane rows and no-folding controls remain correct. | met | Mixed: [`test_mixed_group_keeps_header_only_points`](../../../tests/integration/test_all_point_group_header_1660.py) (`planned:s1:s1`, `planned:group-header:a:p1`). No folding: [`test_no_folding_control_keeps_one_row_per_point`](../../../tests/integration/test_all_point_group_header_1660.py) (one row per point, no header occurrences). Explicit and lane rows: no new #1660-specific test, but the pre-existing suites that declare `rows.mode: explicit` and `rows.mode: lanes` pass on this base (59 and 81 passed, listed above), and View composition now sets `rows_resolved=True` for them too. Honest limit: explicit and lane rows are covered by those existing suites, not by a dedicated #1660 twin. | — |
| 7 | List public SVG/Scene changes with counts. | met | [PR #1670 body](https://github.com/tya5/chrona/pull/1670): 0 of 50 public slides change (0 routes, 0 labels, 0 primitives, 0 diagnostics). Re-measured here: `git diff --stat be89bcd5d~1 be89bcd5d -- examples` and `git diff --stat be89bcd5d e71c8de3d -- examples` are both empty, so the PR and its bot commit changed no public SVG or Scene. `tools/regenerate_public_examples.py --check` was not re-run here; the 0 of 50 count rests on the PR body plus the empty example diffs. | — |
| 8 | Inspect actual PNG output. | met | PNG of the issue repro rendered on this base and opened: [all-point-group-header.png](assets-1660/all-point-group-header.png) (7.6 KB). It shows the title, a Jan/Feb 2026 axis, a single "Team a" header band, and the two diamonds "One" (12 Feb) and "Two" (16 Feb) with their labels on that header. There is no ordinary row beneath it, no empty row and no duplicate mark or label. | — |

## Programme-level criteria (optional)

| Issue | Fully met | Open rows |
| --- | --- | --- |
| #1660 | 1, 2, 3, 4, 5, 6, 7, 8 | none |

Public side effects, re-measured:

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| #1670: public examples (0 of 50 slides) | 0 | 0 | 0 | 0 |
| This review (docs and one 7.6 KB PNG) | 0 | 0 | 0 | 0 |

## Architecture conclusion

View folding owns row membership and now says so structurally: a resolved empty row set is a result, an absent one is a legacy projection, and the group order travels with the projection so a group of folded points is still a container. Layout no longer rebuilds rows from items for a resolved projection. All eight rows are met; two limits are recorded, not hidden: explicit/lane rows are covered by existing suites rather than a dedicated twin, and the public-example check was not re-run in this environment. #1660 may close after a green three-OS run containing this review.
