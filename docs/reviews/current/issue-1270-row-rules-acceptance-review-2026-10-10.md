<!-- chrona:literal-acceptance/v1 -->

# Issue #1270 — row rules acceptance

Ready base: `0617e671c51ed14fe0d242a37a18a744bd85b7e8`. [Published design and architecture review](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312). Layout completes row-bottom paths; Scene projects them; Theme supplies decoration paint. No corpus or derived output was authored. Public artifact and release checks remain pending; do not close.

## Literal issue acceptance

### Issue #1270

- Source: [Issue #1270](https://github.com/tya5/chrona/issues/1270)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test Theme/View with `rows: rules` yields exactly one rule per item row and none on header rows. Each rule's y equals its row's bottom edge, and its x extent equals the row band extent (checked from Scene). | met | [Synthetic Scene and SVG tests](../../../tests/integration/test_row_rules.py) verify all four item rows, including group-final rows, full table-to-timeline extent, and header exclusion. | — |
| 2 | Missing role → `E_THEME_ROLE_REQUIRED`. | met | [Missing-role test](../../../tests/integration/test_row_rules.py) checks the code, canonical View pointer, and required Theme role pointer. | — |
| 3 | Corpus without the declaration → unchanged output (existing goldens/ledger pass). | not met | [Absent/none byte test](../../../tests/integration/test_row_rules.py) passes; exact public before/after artifact audit remains required. | — |
| 4 | Do not edit `examples/**`. The reviewer adopts the setting in target B, Title Card, Marquee and Yuya. | met | [Published scope](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312) excludes examples and generated evidence; target adoption is reviewer-owned. | — |

## Programme-level criteria (optional)

None. Focused batch: 100 passed (19.59s), including semantic registry, capabilities, contrast and existing group/tab tests. Independent read-only review found no concrete defect. S0 passed: one declared View enum expansion, 37 equal schema structures, 451 mapped documents/739 probes; four unchanged baseline-invalid fixtures. The provided pruning tool retired six already-landed #927 L1 entries.

[Initial CI](https://github.com/tya5/chrona/actions/runs/37983841717) failed the decoration witness check: row-band and row-rule were incorrectly required independently. The [published design correction](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312) makes them alternatives for one required row-decoration concept, retaining every emitted finding and all other obligations. Correction source `8c85167b9ed2f4eacdda558dd4d83f1ba75b27c4`: 12 tool/registry and seven row-rule tests passed, including either alternative, neither, and missing unrelated decoration; all 19 passed again after the main review merge. Downstream missing-artifact failures resulted from the preview failure; they are not independent test failures. Replacement exact-head CI/artifacts and exact-main three-OS pytest/conformance/wheel with this review published remain required.
