<!-- chrona:literal-acceptance/v1 -->

# Release review — `missingActualScope: in-progress` with lane rows

Implementation: [#1275](https://github.com/tya5/chrona/pull/1275) (merge `f62d42df`). The lane expected-mark inventory lists the `missing-actual` mark in place of the `actual` mark for a span the View marked in progress, with a typed absence `in-progress-empty-at-cutoff` when the cutoff is not after the actual start; the `E_REVIEW_MISSING_ACTUAL_SCOPE_LANES` refusal is removed. Mark geometry is unchanged. Plan: [Status comment](https://github.com/tya5/chrona/issues/1027).

## Literal issue acceptance

### Issue #1027

- Source: [Issue #1027](https://github.com/tya5/chrona/issues/1027) (body and one Status comment)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | "extend the lane expected-mark inventory (`lane_projection.close_lane_projection`)... for the in-progress mark" | met | [Diff](https://github.com/tya5/chrona/pull/1275/files): `src/chrona/presentation/layout/lane_projection.py` `close_lane_projection` expects `missing-actual` for a span with `missing_actual_mark == "in-progress"` and an actual start (as-of required, empty-at-cutoff absence); `projection.py` no longer raises `E_REVIEW_MISSING_ACTUAL_SCOPE_LANES` (no reference remains in `src`, `schemas`, `docs/specification`). Spec: `docs/specification/06-view-model.md` section 8; `schemas/view-v0.28.schema.yaml` drops "Not available with lane rows". | — |
| 2 | "(and `ExpectedLaneMark` evidence) for the in-progress mark" | met | `ExpectedLaneMark(role="missing-actual", purpose="missing-actual")` is added through `_expect_mark`; asserted (`role`, `purpose`, `placement_id` prefix `missing-actual:`) in `tests/unit/chrona/presentation/layout/test_lane_projection.py::test_in_progress_span_expects_the_missing_actual_mark_in_place_of_the_actual_mark`. | — |
| 3 | "with synthetic lane tests" | met | Same [unit test](../../../tests/unit/chrona/presentation/layout/test_lane_projection.py) (expected marks, as-of required, empty-at-cutoff absence, unmarked Actual unchanged); [`tests/integration/test_missing_actual_scope.py`](../../../tests/integration/test_missing_actual_scope.py)`::test_in_progress_with_lane_rows_draws_the_same_marks_as_automatic_rows`. The PR body records a mutation check that fails the unit test. | — |
| 4 | "default output unchanged" | met | [`tests/integration/test_missing_actual_scope.py`](../../../tests/integration/test_missing_actual_scope.py)`::test_the_default_scope_with_lane_rows_is_unchanged_by_the_in_progress_inventory`; the new branch needs `missing_actual_mark == "in-progress"`, which only the in-progress scope sets. [PR body](https://github.com/tya5/chrona/pull/1275): public slides, routes, labels and primitives changed 0; no `examples/**` edit. The PR states local byte identity was not verified and relies on the CI derived-preview snapshot comparison; no committed generated evidence changed. | — |

## Programme-level criteria (optional)

None.
