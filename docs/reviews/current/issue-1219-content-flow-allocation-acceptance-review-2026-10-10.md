<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — content-sized Flow block allocation (#1219)

Implementation: [#1277](https://github.com/tya5/chrona/pull/1277) (merge `eb4e83fd`). A row or column allocated a content-sized Flow child its tallest child's height while arrangement wraps it into a line stack, so the host came out too short and raised a false `W_LAYOUT_VISIBLE_OVERFLOW`. `_Arranger._linear` now allocates a Flow child its natural line stack at the inline extent it is arranged at (`_natural_child_block`, which uses `_flow_lines`); the footer-successor correction no longer translates a successor twice (`complete_footer_band`). Rule: Specification 33 section 13.1. Plan: [Status comment](https://github.com/tya5/chrona/issues/1219#issuecomment-6084095427).

## Literal issue acceptance

### Issue #1219

- Source: [Issue #1219](https://github.com/tya5/chrona/issues/1219)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic finite content-sized Flow: known inline width causes two lines, allocated block encloses both line heights plus gap; no spurious track overflow. | met | [`test_content_flow_block_allocation.py`](../../../tests/unit/chrona/presentation/layout/test_content_flow_block_allocation.py) `test_a_known_inline_width_that_wraps_two_lines_allocates_both_lines_without_a_track_overflow` (allocated 60 = 20 + 40, children on separate lines, no warning). | — |
| 2 | Synthetic one-line, nested/container, min/max and genuinely insufficient declared host cases retain intended allocation and honest overflow. | narrowed | One-line (`test_one_line_keeps_the_tallest_child`), a too-small fixed host (`test_a_fixed_host_that_is_genuinely_too_small_keeps_its_honest_overflow`), a `fitContent` host and a Flow in a row are covered in [the same file](../../../tests/unit/chrona/presentation/layout/test_content_flow_block_allocation.py). Only a Flow that is a direct child of a row or column is completed: a Flow nested inside a further container (a column in a column) keeps its earlier allocation and is not covered by a test. | [Open on the issue](https://github.com/tya5/chrona/issues/1219): complete a Flow nested in a non-flow container, with a synthetic fixture. |
| 3 | Layout owns geometry; no Scene/adapter measurement or corpus edits. | met | [Diff](https://github.com/tya5/chrona/pull/1277/files): `layout/engine.py`, `layout/surface_content.py` and Spec 33 only; no Scene, adapter or `examples/**` change. | — |
| 4 | Disclose public SVG/Scene/diagnostic effects from one snapshot; focused tests and planned release gates pass. | met | [PR body](https://github.com/tya5/chrona/pull/1277): a materialize pass over all 70 slides (43 changed: footer overflow removed on all, canvas block size +14.8 on 28, other growth on 11, shrink of 25 to 31 px on 4), the four shrinking and the 28 growing slides inspected before and after; layout suite 1356 and the footer-successor tests pass; PR checks and the merge are on the [PR](https://github.com/tya5/chrona/pull/1277/checks). The snapshot is a local materialize pass, not one CI artifact. | — |
| 5 | 2026-10-07 comment: a Flow child's declared `inlineSize: fixed` is ignored by `_flow_lines` (it uses `max(itemMinInlineSize, preferred_inline)`); resolve child inline declarations consistently for natural demand and arrangement, with synthetic fixed, minmax and content cases. | deferred | Not in this slice (stated in the [Status comment](https://github.com/tya5/chrona/issues/1219#issuecomment-6084095427)): it is an inline-declaration change with its own corpus effects. | [Open on the issue](https://github.com/tya5/chrona/issues/1219): the Flow child inline-declaration resolver. |

## Programme-level criteria (optional)

None. The issue stays open for rows 2 and 5.
