<!-- chrona:literal-acceptance/v1 -->

# Issue #1062: per-column table text role and legend label colour, acceptance review

Source: [Issue #1062](https://github.com/tya5/chrona/issues/1062), re-fetched 2026-10-04 after the merges (body unchanged, 1838 characters; three comments, all this work's claim, decision and status blocks, no new acceptance rows). The issue has an acceptance list; the rows below are its six literal bullets. Work record: [issue-1062-text-roles-2026-10-04.md](../planning/active/issue-1062-text-roles-2026-10-04.md); living contracts [Specification 24](../../specification/24-table-timeline-presentation.md) (`textRole`), [Specification 07](../../specification/07-style-and-theme.md) and [Specification 49](../../specification/49-semantic-presentation-contract.md).

Slices: design record [PR #1086](https://github.com/tya5/chrona/pull/1086) (`86f85498`); implementation [PR #1091](https://github.com/tya5/chrona/pull/1091) (`803fe08e`). The PR had conformance, three pytest shards, newest-Python reproduction, mcp-floor and derived-ready green on its final head before merge, on a base equal to the `main` tip.

## Literal issue acceptance

### Issue #1062

- Source: [Issue #1062](https://github.com/tya5/chrona/issues/1062)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A table whose second column names a secondary role: every text primitive of that column carries the role's colour and size, and the other columns are unchanged. | met | [`test_text_roles.py`](../../../tests/integration/test_text_roles.py) `test_the_named_role_sets_the_size_and_colour_of_that_column_only`: both Phase cells have font size 9 and visual role `table-cell-secondary` with a fill different from the default; the Work package cells keep size, fill and role. A state-coloured cell in a named-role column keeps its own ink and takes the role's size (`test_a_state_coloured_cell_keeps_its_ink_and_takes_the_role_type`), disclosed below. | none |
| 2 | A legend with a declared label role: every legend text carries it. | met | [`test_text_roles.py`](../../../tests/integration/test_text_roles.py) `test_the_legend_labels_all_carry_the_declared_ink`: with `legend.fill` bound, every `legend-label` Text carries role `legend` and the declared fill, positions unchanged. The label size is the Theme role `legend`'s existing `fontSize` (the legend slot already measures in it, #497); no new role name was introduced (decision on the issue). | none |
| 3 | Absent declarations give byte-identical output. | met | `python tools/regenerate_public_examples.py --check` on the PR: all 57 slides pass, every existing slide byte identical (only the new slide is new); [`test_text_roles.py`](../../../tests/integration/test_text_roles.py) `test_absent_declarations_are_byte_identical` compares the surfaces of a Theme with an unused role against none. Seven mutations (role selection, cell paint, state-cell guard, unknown-role check, its pointer, the classification clause, legend paint) each fail a test. | none |
| 4 | An unknown role name fails at its pointer. | met | [`test_text_roles.py`](../../../tests/integration/test_text_roles.py) `test_an_unknown_role_fails_at_the_view_pointer`: `RenderFailed` `E_THEME_ROLE_REQUIRED` with `source_ref` `/body/tableColumns/1/textRole` and the missing `/body/roles/no-such-role` in the message, raised before any measurement. | none |
| 5 | A label under the role that fails text contrast is reported as it is today. | met | [`test_text_roles.py`](../../../tests/integration/test_text_roles.py) `test_a_muted_ink_that_fails_text_contrast_is_reported_and_a_passing_one_is_not` and `test_a_legend_ink_that_fails_text_contrast_is_reported`: a named-role fill equal to the ground gives `E_SCENE_STATE_TEXT_CONTRAST` errors at floor 4.5, `textMuted` passes. This needed a gate fix, found while reading: `contrast_binding_for` did not classify Text painted in a role of its own, so these inks (and the #991 `tableColumnLabel` header) were not checked at all; a Text whose role is no registered Scene role is now ground text by its purpose (unit test `test_a_theme_text_paint_role_is_ground_text_by_its_purpose`). The committed `table-header` slide's header passes (7.56). | none |
| 6 | Target B declares a muted Phase column and muted legend labels. | narrowed | Owner scope rule for this work: the reviewer's `examples/halcyon-1/*target-b*` files are not edited; adopting the knobs there is the reviewer's step (reviewer PR #1061, [#987](https://github.com/tya5/chrona/issues/987)). Both knobs exist, are documented in Specifications 24, 07 and 49 and work on the Controller Z slide `text-roles` (below). | [#987](https://github.com/tya5/chrona/issues/987) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

View declares `textRole` (intent only); Theme declares size and colour; Layout measures and places in the named role through the existing cell typography channel; Scene picks the paint role; adapters are unchanged. One optional property in `view-v0.28` (`schema_equivalence --base-rev origin/main` PASS, no expected-delta entry, no pruning). `legend` becomes a text role admitting `fill` and `opacity`; a View-named role is admitted for measurement and `fill`, and the closed-vocabulary role-admission test states that one exception (Text, purpose `table-cell`) instead of skipping unknown roles. Decisions and how to reverse each are on the issue.

Disclosures:

- Rendered image read (`examples/controller-z/generated/text-roles.svg`, regenerated by derived-sync, rasterized with the packaged fonts): the Team column is 12 px in `textMuted` against 14 px Workstream and Finish cells, row heights unchanged; the delta column keeps its state colour; the legend labels "Planned" and "Actual" are muted and the swatches keep their colour. Comparison with the mock `02-programme-board.png`: the mock's Phase column and legend read the same way (smaller, muted grey, ink elsewhere); this slide's column is a team name and its Theme is Controller Z's, so only the mechanism, not the corpus look, is compared. The column header "Team" stays in `text` by design (a column's role is for its cells; headers have `tableColumnLabel`).
- Adapters: SVG, Typst and TikZ output for the slide's synthetic twin carry the 9 pt size and the muted ink for cells and legend labels (`test_every_adapter_serialises_the_role_size_and_ink_of_the_column_and_the_legend`); no adapter reads a role name.
- State-coloured cells (variance, missing actual) in a named-role column take the role's typography but keep their state ink (decision on the issue), so a muted column does not mute a variance.
- An open role name for `textRole` also needs the Theme to declare only text measurement properties and `fill` (`iconScale` and `iconGap` are not admitted for an open name and a cell does not use them).
- Not read image by image: nothing else changed (every other slide is byte identical).

Exact review-bearing-main three-OS CI must pass before closing #1062; that run is recorded in the closing comment.
