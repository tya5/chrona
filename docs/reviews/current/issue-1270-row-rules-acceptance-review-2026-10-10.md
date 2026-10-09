<!-- chrona:literal-acceptance/v1 -->

# Issue #1270 — row rules acceptance

Ready source base: `d4c93f64ae888d335c0aa4b412e05686894bf76b`. [PR #1314](https://github.com/tya5/chrona/pull/1314), reviewed head `4da0b28c243094af931ed13cff3589d8627be29a`, merged at `8915b4598c35b89561ac07b7edaf7af3d018f7cb`. [Published design and architecture review](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312). Layout completes row-bottom paths; Scene projects them; Theme supplies decoration paint. No corpus or derived output was authored. Final review publication and exact-main release remain pending; do not close.

## Literal issue acceptance

### Issue #1270

- Source: [Issue #1270](https://github.com/tya5/chrona/issues/1270)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test Theme/View with `rows: rules` yields exactly one rule per item row and none on header rows. Each rule's y equals its row's bottom edge, and its x extent equals the row band extent (checked from Scene). | met | [Synthetic Scene and SVG tests](../../../tests/integration/test_row_rules.py) verify all four item rows, including group-final rows, full table-to-timeline extent, and header exclusion. | — |
| 2 | Missing role → `E_THEME_ROLE_REQUIRED`. | met | [Missing-role test](../../../tests/integration/test_row_rules.py) checks the code, canonical View pointer, and required Theme role pointer. | — |
| 3 | Corpus without the declaration → unchanged output (existing goldens/ledger pass). | met | [Absent/none byte test](../../../tests/integration/test_row_rules.py); [exact-head artifact audit](https://github.com/tya5/chrona/pull/1314#issuecomment-6088989633): all 70 SVG and 70 Scene files byte-identical, no added/retired paths. Only three intended diagnostic/coverage reports change. | — |
| 4 | Do not edit `examples/**`. The reviewer adopts the setting in target B, Title Card, Marquee and Yuya. | met | [Published scope](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312) excludes authored examples and generated evidence. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) explicitly makes target adoption the reviewer's step, not a dev closing condition; reviewer completion is not claimed. | — |

## Programme-level criteria (optional)

None. Focused batch: 100 passed (19.59s), including semantic registry, capabilities, contrast and existing group/tab tests. Independent read-only review found no concrete defect. S0 passed: one declared View enum expansion, 37 equal schema structures, 451 mapped documents/739 probes; four unchanged baseline-invalid fixtures. The provided pruning tool retired six already-landed #927 L1 entries.

[Exact-head CI](https://github.com/tya5/chrona/actions/runs/37988094523) passed every check, including all three PR pytest shards, conformance, newest-Python materializers and derived-ready. The [published coverage correction](https://github.com/tya5/chrona/issues/1270#issuecomment-6088015312) treats row-band/row-rule as alternatives while retaining all emitted contrast findings; focused correction tests: 19 passed, diagnostic ratchet: one passed. The original witness failure and consequent missing-artifact failures are resolved, not waived.

Required release evidence: automatic derived sync, publication of this final review, then successful three-OS pytest/conformance/wheel on the exact published main containing it.
