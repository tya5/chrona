<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — vertical text refinements (#981)

Implementation: [#1256](https://github.com/tya5/chrona/pull/1256) (head `dfeaeee4`). The issue's acceptance is that each listed refinement "is declared as a Theme knob or rule with a synthetic test, or recorded as deliberately out of scope". Plan and dispositions: [Status comment](https://github.com/tya5/chrona/issues/981#issuecomment-6069006964). Rule text: Specification 07, the vertical writing paragraph.

## Literal issue acceptance

### Issue #981

- Source: [Issue #981](https://github.com/tya5/chrona/issues/981)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | OpenType `vert`/`vrt2` substitution is declared as a knob or rule with a synthetic test, or recorded as deliberately out of scope. | met | Recorded as deliberately out of scope in [Spec 07](https://github.com/tya5/chrona/pull/1256/files) (it needs shaping in every adapter, while Layout completes per-segment Text only). | — |
| 2 | tate-chu-yoko is declared as a knob or rule with a synthetic test, or recorded as deliberately out of scope. | met | Recorded as deliberately out of scope in [Spec 07](https://github.com/tya5/chrona/pull/1256/files) (an upright multi-digit cell needs the same shaping). | — |
| 3 | More than one column is declared as a knob or rule with a synthetic test, or recorded as deliberately out of scope. | met | Recorded as deliberately out of scope in [Spec 07](https://github.com/tya5/chrona/pull/1256/files); the cut is no longer silent (row 6) and a short tag is the group header template (#583). | — |
| 4 | Alignment (centre or end alignment is not a knob) is declared as a knob or rule with a synthetic test, or recorded as deliberately out of scope. | met | Knob: `align` (`start`, `center`, `end`) on a vertical `groupHeader`; refused on a horizontal one with `E_THEME_ROLE_PROPERTY_UNSUPPORTED`; `python -m tools.schema_equivalence --base-rev origin/main` PASS ([diff](https://github.com/tya5/chrona/pull/1256/files)). Tests in `tests/integration/test_vertical_writing.py`: `test_align_places_a_short_tag_at_the_start_the_middle_or_the_end_of_its_rows`, `test_without_align_the_tag_is_start_aligned_as_before`, `test_align_on_a_horizontal_group_header_is_refused`. | — |
| 5 | Other roles (`writingMode` admitted on `groupHeader` only) is declared as a knob or rule with a synthetic test, or recorded as deliberately out of scope. | met | Recorded as deliberately out of scope in [Spec 07](https://github.com/tya5/chrona/pull/1256/files); the existing rejection on other roles is pinned by `test_a_role_that_does_not_support_a_writing_mode_is_rejected_by_the_existing_diagnostic`. | — |
| 6 | Post-review comment: long vertical tags are silently truncated; at least report silent truncation of a group's name, and decide between a declared short tag, more columns, or a growing band. | met | Rule: a tag cut to its rows is `W_LAYOUT_TEXT_ELLIPSIZED` (`group-tag-text`, source kept), or `W_LAYOUT_VISIBLE_OVERFLOW` when not even the ellipsis fits: `test_a_tag_cut_to_its_rows_is_reported_with_its_source`, `test_a_tag_that_fits_reports_nothing` ([tests](https://github.com/tya5/chrona/pull/1256/files)). Decision: the declared short tag is the group header template (#583); more columns and a growing band are not offered. Side effect: 5 new warnings on `halcyon-1/gallery-vertical-group-tags`, no primitive changes ([PR body](https://github.com/tya5/chrona/pull/1256)). | — |

## Programme-level criteria (optional)

None.
