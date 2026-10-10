<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — nested flow natural measurement and arrangement width (#1206)

Implementation: [#1258](https://github.com/tya5/chrona/pull/1258) (merge `01d47842`). `engine._flow_lines` measured a flow item's natural block at `min(line, width)` but arranged it at the full `width`. Contract decision against Specification 33 section 13 (natural sizes are kept, overflow is diagnosed, nothing is shrunk): a flow item is arranged at its natural width and its natural block is measured at that same width. Plan and contract: [Status comment](https://github.com/tya5/chrona/issues/1206#issuecomment-6069688849). Rule: Specification 33 section 13.1.

## Literal issue acceptance

### Issue #1206

- Source: [Issue #1206](https://github.com/tya5/chrona/issues/1206)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Natural measurement and arrangement use the same completed inline extent for nested content-sized flow children; synthetic narrow/wide fixtures agree on wrapping and block extent. | met | [`test_nested_flow_inline_extent.py`](../../../tests/unit/chrona/presentation/layout/test_nested_flow_inline_extent.py) `test_natural_measurement_and_arrangement_agree_on_the_nested_flow_block_extent` (viewports 100, 119, 120, 200: natural 40, arranged inner 120 x 40, children on one line) and `test_a_flat_flow_still_wraps_at_the_bounded_inline_extent`; the issue's reproduction (measured 60, arranged 40) now gives 40 and 40. | — |
| 2 | Preserve explicit fixed/intrinsic/bounded/flexible/aspect size contracts and finite diagnosed overflow. | met | Those contracts are applied after the measurement from the same `width`; the item is never shrunk, so the existing `W_LAYOUT_VISIBLE_OVERFLOW` still reports an overrun ([diff](https://github.com/tya5/chrona/pull/1258/files)); the layout unit suite (1345) passes, including the updated `test_content_sized_flow_child_keeps_width_dependent_natural_height_callback`. | — |
| 3 | Report actual corpus side effects without modifying examples to absorb them. | met | [PR body](https://github.com/tya5/chrona/pull/1258): a materialize pass over all 68 slides, all byte-identical; no `examples/**` edit. | — |

## Programme-level criteria (optional)

None. The issue's own requirement to decide the general inline overflow/shrink contract before correcting is recorded in the Status comment above: natural sizes are kept, shrinking to the line was rejected.
