<!-- chrona:literal-acceptance/v1 -->

# Issue #1283 — text-sized group-header band acceptance

Validation source: `62ed63a33596e5717383f547c91d3599e3e2c2b9`, ordinarily adopting exact ready main `484f5cd83ac24e91b7d435be18dfb5be1ebade04` and the batched final acceptance records. [Selected design, architecture review and publication plan](https://github.com/tya5/chrona/issues/1283#issuecomment-6087767756). Layout consumes completed geometry; Scene/adapters do not measure or fit bands. PR artifact/checks and final-review-containing exact-main release remain pending; do not close.

## Literal issue acceptance

### Issue #1283

- Source: [Issue #1283](https://github.com/tya5/chrona/issues/1283)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `groupHeaderBand: text` the group-header-band Rect's inline size equals the measured text inline size plus the declared padding, for every group and for both plain and role-marked templates. | met | [Synthetic Scene and actual SVG tests](../../../tests/integration/test_group_header_text_extent.py): both groups, plain/marked runs, declared inset and start/end tab reservation; all-suppressed runs retain only the leading interval. | — |
| 2 | The band never exceeds the table column; an over-long header ends at the column edge under the existing overflow rule. | met | Same tests verify the table-edge clamp and unchanged visible-overflow text; [Layout unit tests](../../../tests/unit/chrona/presentation/layout/test_surface_groups.py) cover both-end clamping, zero width and missing-closure refusal. | — |
| 3 | Profiles without it are byte-identical. Synthetic fixture test. | met | [Independent frozen pre-change geometry replay](../../../tests/integration/test_group_header_text_extent.py) compares full Scene documents, serialized Scene and SVG bytes for all three legacy extents, plain/marked and folded/unfolded. Vertical cells, group selection and disabled bands are also tested. Fresh public corpus artifact audit remains a release gate. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | Product changes are Layout, shared schema/inventory, Spec50 and synthetic tests; separately committed final records/archives are documentation only. No authored `examples/**` changes. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) makes target adoption reviewer-owned, not a dev closing condition; no reviewer-completion claim. | — |

## Programme-level criteria (optional)

None. After source adoption, integration/vocabulary batch: 83 passed (37.98s); earlier header text/run batch: 107 passed. Final ready-base adoption changes only generated diagnostic inventory, not tested product code. Fresh L1 against exact ready 484f5: 37 equal and one declared group-header extent delta, no stale findings; full S0 and inventory/import/delivery checks passed earlier. Direct legacy-byte replay remains in the integration tests. Required next gates: one product PR including separate final-record commits, exact-head artifact/checks, then final-review-containing main three-OS release. No local full pytest or authored corpus regeneration.
