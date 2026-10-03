<!-- chrona:literal-acceptance/v1 -->

# Issue #1065: indent child rows under field-grouping headers, acceptance review

Source: [Issue #1065](https://github.com/tya5/chrona/issues/1065), re-fetched 2026-10-04 after the merges (body unchanged, 1451 characters; two comments, both this work's claim and status blocks, no new acceptance rows). The issue has an acceptance list; the rows below are its five literal bullets. Work record: [issue-1065-1064-field-group-indent-and-slot-heading-2026-10-04.md](../planning/active/issue-1065-1064-field-group-indent-and-slot-heading-2026-10-04.md); living contract [Specification 24](../../specification/24-table-timeline-presentation.md) section 2.1 and [Specification 45](../../specification/45-slide-grade-review-vocabulary.md).

Slices: design record [PR #1093](https://github.com/tya5/chrona/pull/1093) (`a4db315b`); implementation [PR #1094](https://github.com/tya5/chrona/pull/1094) (`7437f471`). The PR had conformance, three pytest shards, newest-Python reproduction and derived-ready green on its final head before merge.

## Literal issue acceptance

### Issue #1065

- Source: [Issue #1065](https://github.com/tya5/chrona/issues/1065)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Field grouping with headers and a declared indent: each child row's label starts exactly `indent` after its header's label start. | met | [`test_group_child_indent.py`](../../../tests/integration/test_group_child_indent.py) `test_every_child_label_starts_exactly_one_step_after_its_header_label` (synthetic Project through the packaged `executive-light` bundle, no `examples/` input): all four child labels of two groups start exactly the Theme's `table.indent.inlineSize` after the one header label start. Beside a start group tab the step is still counted from the header label (`test_a_start_group_tab_leads_the_header_label_and_the_children_follow_it`); a later hierarchy column counts from its own start (`test_a_later_hierarchy_column_is_indented_from_its_own_start_even_beside_a_tab`). Seven mutations of the rule (tab lead, extra inset, measurement, vertical tag, depth rule, first-column lead, contract) each fail a test. | none |
| 2 | Header labels are unchanged. | met | [`test_group_child_indent.py`](../../../tests/integration/test_group_child_indent.py) `test_header_labels_and_unindented_cells_are_unchanged`: the group-header primitives' starts are identical with and without `hierarchyColumn`; only the cells of the named column move, each by exactly the step. | none |
| 3 | The hierarchy-grouping fixtures give byte-identical output. | met | `python tools/regenerate_public_examples.py --write` on the PR left all earlier public slides byte identical (the corpus includes the HALCYON-1 hierarchy-grouping and explicit-depth slides; only the new slide is new). [`test_the_other_nesting_rules_are_not_replaced`](../../../tests/integration/test_group_child_indent.py) pins that hierarchy grouping, a row `depth` and a `parentRow` never take the new rule, and that `table_cell_indent` keeps its arithmetic. | none |
| 4 | The flat case behaves as specified. | met | Field grouping with `presentation: band` or none, plus `hierarchyColumn`, stays `E_VIEW_HIERARCHY_COLUMN_UNEXPECTED` (decision D3 on the issue; message now names "field grouping with presentation header"): [`test_header_group_hierarchy_column.py`](../../../tests/unit/chrona/presentation/contracts/test_header_group_hierarchy_column.py) and `test_without_header_groups_the_declaration_stays_an_error` (end to end, by diagnostic id). A vertical group tag draws no header row and no indent (`test_a_vertical_group_tag_draws_no_header_row_and_no_indent`). | none |
| 5 | Target B declares the indent. | narrowed | Owner scope rule for this work: the reviewer's `examples/halcyon-1` 21-target-b files are not edited; adopting a knob there (declare `hierarchyColumn` and a `table.indent.inlineSize` step) is the reviewer's step (reviewer PR #1061, [#987](https://github.com/tya5/chrona/issues/987)). The knob exists, is documented in Specification 24 section 2.1 and works on the Controller Z slide `group-child-indent` (below). | [#987](https://github.com/tya5/chrona/issues/987) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

View names the indented column (the existing `hierarchyColumn`, now accepted under non-hierarchy grouping with header presentation); Theme owns the step (the existing required metric `table.indent.inlineSize`); Layout owns the arithmetic in one helper (`header_group_cell_indent`) used by both the table measurement (`sources.py`, so a content-sized table is never narrower than its widest indented label) and the placement (`surface_table.py`); Scene and adapters are unchanged. No schema change (`schema_equivalence --base-rev origin/main` PASS); the previously rejected combination becomes valid and every accepted document renders as before.

Disclosures:

- Rendered image read (`examples/controller-z/generated/group-child-indent.svg`, regenerated by derived-sync): the header labels "Firmware", "System Validation" and "Product Engineering" start at the table edge and each work item starts one step (16 px) to the right of its header label. Honest comparison with the mock `02-programme-board.png`: the mock insets the header label from the band edge by half a step and the child by one step beyond it; this slide's executive Theme draws no header band fill, and the header label sits at the table edge because the Theme declares no group tab or header inset, which is the Theme's choice, not Layout's.
- Not read image by image: nothing else changed (all other slides are byte identical).
- A header-group child is indented from the header's label start; the hierarchy rule's `inset` term is deliberately not added (it belongs to hierarchy grouping and its output must not change).

Exact review-bearing-main three-OS CI must pass before closing #1065; that run is recorded in the closing comment.
