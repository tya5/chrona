<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — visual leftovers from #882 and #588

No product code changed. Each item was re-checked against `main` at `f0fb4018` and the committed `controller-z` evidence (derived-sync `6dd2a678`); the plan is the [Status comment](https://github.com/tya5/chrona/issues/988#issuecomment-6068098705). Items 2 and 3 were already resolved by earlier work; item 1 needs only a Theme value in an example, which is the reviewer's step (`examples/**` is reviewer-owned).

## Literal issue acceptance

### Issue #988

- Source: [Issue #988](https://github.com/tya5/chrona/issues/988)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Item 1: the group tab's aspect ratio; check that `tabInlineSize` and `tabBlockSize` can express the target, and set them in the target YAML (#987); if not, file the missing knob. | deferred | Both knobs exist and are tested: [`test_group_tab.py`](../../../tests/integration/test_group_tab.py) (`test_the_block_size_defaults_to_the_header_and_an_explicit_one_is_kept`, a near-square tab is `tabInlineSize` equal to `tabBlockSize`); no missing knob. The [group-tabs Theme](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/themes/group-tabs.yaml) declares only `tabInlineSize: 56`, so the committed [SVG](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/group-tabs.svg) draws 56 x 20 tabs. Setting `tabBlockSize` and the inline size there is an `examples/**` edit. | [Reviewer step](https://github.com/tya5/chrona/issues/988#issuecomment-6068098705): set the tab size tokens in `examples/controller-z/themes/group-tabs.yaml` and regenerate. |
| 2 | Item 2: the quarter and month labels on `group-tabs` collide (`2026 Q1 / Mar`) and the row spacing is loose; fix the YAML, or the rule with a synthetic test. | met | Not reproducible on `main`: in the committed [group-tabs SVG](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/group-tabs.svg) the quarter labels (`axis-label:2:*`) are at y 80.8 and the month labels (`axis-label:3:*`) at y 95.2, separate tier baselines 14.4 px apart at 12 px type. No rule defect, so no rule change or new test; the row-spacing value is a Theme/Layout Profile value of the example. | — |
| 3 | Item 3: on `value-affixes` the affix renders as `+4 !` with a gap; make the affix join flush by default or offer a declared gap defaulting to 0. | met | The committed [value-affixes SVG](https://github.com/tya5/chrona/blob/abbe91a40b46621e448eded6dcfb42b1dd97bb7b/examples/controller-z/generated/value-affixes.svg) draws `+4!` flush (`cell:firmware:Δ`). The affix is joined with no gap in `v05_content.cell_parts`, pinned by [`test_table_affixes_render.py`](../../../tests/integration/test_table_affixes_render.py) (`test_a_content_column_is_exactly_as_wide_as_with_the_affixes_typed_into_the_values`). | — |
| 4 | Each item is fixed or explained, with PNG evidence. | narrowed | Each item is explained above and in the [Status comment](https://github.com/tya5/chrona/issues/988#issuecomment-6068098705), with coordinates from the committed SVG evidence; no PNG is attached because items 2 and 3 are unchanged committed output and item 1 changes only after the reviewer's example edit. | [Reviewer step](https://github.com/tya5/chrona/issues/988#issuecomment-6068098705): attach the PNG when the tab sizes are set. |

## Programme-level criteria (optional)

None.
