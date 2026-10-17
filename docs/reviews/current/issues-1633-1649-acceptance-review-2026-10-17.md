<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #1633, #1649

Observed on `main` at `5e0690514` (contains #1651 and #1652); #1649 row 3 was re-verified on `84a5abcde` (contains #1656), see that row. Criteria are copied from the issue bodies and the comments fetched on 2026-10-17 (`gh issue view N --comments`). Synthetic twins were run on this base (`pytest tests/integration/test_auto_height_legend_notes_reserve.py tests/integration/test_lane_table_default_header.py`: 9 passed). Trial 3 input is `trial3/project.yaml` from branch `reviewer/trial3-inputs`, rendered here as SVG at the default 1600xauto with `technical-print`, `wallboard-dark` and `editorial`. `tools/regenerate_public_examples.py --check` could not be run in this environment (the editable install resolves schemas to another checkout), so public counts below are the ones disclosed in the PR bodies, not re-measured.

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #1633 | [#1651](https://github.com/tya5/chrona/pull/1651) (default lane header reads `Task` when every lane is generated one per object), [#1652](https://github.com/tya5/chrona/pull/1652) (item b, tracked as #1649) | none |
| #1649 | [#1652](https://github.com/tya5/chrona/pull/1652) | none |

## Literal issue acceptance

### Issue #1633

- Source: [Issue #1633](https://github.com/tya5/chrona/issues/1633)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace for each of the three. | met | The [trace comment](https://github.com/tya5/chrona/issues/1633#issuecomment-6231706599) traces (a) the axis window (Spec 06 section 7 padding, not the as-of date), (b) the empty band (legend conservative stack and empty notes in the auto floor) and (c) the editorial `Lane` header (literal default column in `_lane_table_content`). The reviewer's [decisions on the traces](https://github.com/tya5/chrona/issues/1633#issuecomment-6231723505) state "row 1 met (traces)". | — |
| 2 | Each either fixed with a synthetic twin or recorded as by-declaration with the declaration the reviewer should change. | met | (a) Recorded by specification, not fixed: the reviewer decision says "Record (a) as by-specification, not a defect" and keeps the padding rule in [Spec 06](../../specification/06-view-model.md) section 7; the trace names `window: {mode: explicit, start, end}` as the only project-level knob. No preset declaration is to change. (b) Fixed by [#1649](https://github.com/tya5/chrona/issues/1649) / [PR #1652](https://github.com/tya5/chrona/pull/1652) with twins in [`tests/integration/test_auto_height_legend_notes_reserve.py`](../../../tests/integration/test_auto_height_legend_notes_reserve.py); acceptance of that fix is graded in the #1649 rows below, all met. (c) Fixed by [PR #1651](https://github.com/tya5/chrona/pull/1651) (`_default_lane_header`; rule in [Spec 38](../../specification/38-review-row-composition.md)) with twins [`test_generated_one_per_object_lanes_read_task`, `test_declared_lane_keys_read_lane`, `test_shared_generated_lanes_read_lane`, `test_explicit_columns_are_unchanged`](../../../tests/integration/test_lane_table_default_header.py), which pass on this base. Public effect of (c) per the PR body: 2 of 50 slides, 1 label each (`Lane` to `Task`). | — |

### Issue #1649

- Source: [Issue #1649](https://github.com/tya5/chrona/issues/1649)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic twin: an inline line legend with N entries that wraps to k rows reserves k rows, not N. | met | [`test_a_wrapping_inline_legend_reserves_the_rows_it_wraps_to_not_every_entry`, `test_a_legend_that_fits_one_row_reserves_one_row`, `test_an_inline_legend_without_a_wrap_rule_is_one_row_not_a_stack`, `test_a_fixed_height_canvas_is_unchanged_by_the_narrowing`](../../../tests/integration/test_auto_height_legend_notes_reserve.py) pass on this base. Rule in [Spec 33](../../specification/33-intent-oriented-layout.md) (legend paragraph); code `wrapped_legend_line_block` in [`surface_legend.py`](../../../src/chrona/presentation/layout/surface_legend.py). | — |
| 2 | Synthetic twin: an empty notes source reserves nothing; a non-empty one is unchanged. | met | [`test_an_empty_notes_source_reserves_nothing_and_a_non_empty_one_keeps_its_slot`](../../../tests/integration/test_auto_height_legend_notes_reserve.py) passes on this base. | — |
| 3 | Trial 3 `project.yaml` at 1600x auto on technical-print, wallboard-dark and editorial: no empty band under the legend, viewed as PNG. | met | Re-verified on `main` at `84a5abcde` (contains [PR #1656](https://github.com/tya5/chrona/pull/1656)) by rendering `trial3/project.yaml` (from `dbbce45e60392b7b0be788f841fe2673f4830944`) with `chrona render --preset P --output P.png`, 1600xauto, then viewing the PNGs. Sizes 1600x1969, 1600x1714, 1600x1731. In each the single legend row sits directly under the chart band with normal page padding below it, and no `W_LAYOUT_VISIBLE_OVERFLOW` is in the output of any of the three. PNGs: [technical-print](assets-1649/trial3-technical-print-1600xauto-after-1656.png), [wallboard-dark](assets-1649/trial3-wallboard-dark-1600xauto-after-1656.png), [editorial](assets-1649/trial3-editorial-1600xauto-after-1656.png). The wallboard-dark legend overflow found in the earlier version of this review (a float vs Decimal 16.8 mismatch) is fixed by [PR #1656](https://github.com/tya5/chrona/pull/1656), twin [`test_wallboard_dark_legend_row_fits_its_slot_without_a_visible_overflow_warning`](../../../tests/integration/test_auto_height_legend_notes_reserve.py), which passes. | — |
| 4 | Public SVG/Scene changes listed with counts. | met | Listed in the [Status comment](https://github.com/tya5/chrona/issues/1649#issuecomment-6231807555) and in the [PR #1652 body](https://github.com/tya5/chrona/pull/1652): 9 public SVGs changed, 9 public Scenes changed, 0 canvas-height changes (all public examples are fixed canvases); aster-ssd overview; controller-z annotation-kinds, annotation-rounded, slot-heading, viewer-fit; halcyon-1 02-programme-board, 12-glyph-gates, 15-gallery-image-notes, 19-gallery-text-compression. Counts are as disclosed; they were not re-measured in this review. | — |

## Programme-level criteria (optional)

| Issue | Fully met | Open rows |
| --- | --- | --- |
| #1633 | 1, 2 | none |
| #1649 | 1, 2, 3, 4 | none |

Public side effects, from the PR bodies (not re-measured here):

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| #1651: public examples (2 slides) | 0 | 2 | 2 | 0 |
| #1652: public examples (9 slides) | 0 | 0 | legend and footer placement | 0 |
| #1656: not measured here | — | — | — | — |
| This review (docs only) | 0 | 0 | 0 | 0 |

## Architecture conclusion

#1633 is closed out by three routes: (a) by specification, (b) by the Layout auto-height rule of #1649, (c) by a View default-header rule. Every #1633 and #1649 row is met. The one row first found not met (#1649 row 3, wallboard-dark legend overflow and no recorded PNG view) was fixed by #1656 and re-verified with committed PNGs. Both issues may close after a green three-OS run containing this review.
