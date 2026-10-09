<!-- chrona:literal-acceptance/v1 -->

# Issue #1283 — text-sized group-header band acceptance

Local implementation: `a463db86a6294b0db939f923f41f18d6c5368f02`, based on published #1284 head `5a7fff0bb19f3dbbe0739c5e5da926b183ba77ae`. [Selected design and architecture review](https://github.com/tya5/chrona/issues/1283#issuecomment-6087767756). Layout consumes completed content geometry; Scene and adapters do not measure or fit bands. Public PR/artifact acceptance and final-review-containing exact-main release remain pending; do not close.

## Literal issue acceptance

### Issue #1283

- Source: [Issue #1283](https://github.com/tya5/chrona/issues/1283)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `groupHeaderBand: text` the group-header-band Rect's inline size equals the measured text inline size plus the declared padding, for every group and for both plain and role-marked templates. | met | [Synthetic Scene and actual SVG tests](../../../tests/integration/test_group_header_text_extent.py): both groups, plain/marked runs, declared inset and start/end tab reservation; all-suppressed runs retain only the leading interval. | — |
| 2 | The band never exceeds the table column; an over-long header ends at the column edge under the existing overflow rule. | met | Same tests verify the table-edge clamp and unchanged visible-overflow text; [Layout unit tests](../../../tests/unit/chrona/presentation/layout/test_surface_groups.py) cover both-end clamping, zero width and missing-closure refusal. | — |
| 3 | Profiles without it are byte-identical. Synthetic fixture test. | met | [Independent frozen pre-change geometry replay](../../../tests/integration/test_group_header_text_extent.py) compares full Scene documents, serialized Scene and SVG bytes for all three legacy extents, plain/marked and folded/unfolded. Vertical cells, group selection and disabled bands are also tested. Fresh public corpus artifact audit remains a release gate. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | Authored changes are Layout, shared schema/inventory, Spec50, synthetic tests and this review only. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) makes target adoption reviewer-owned, not a dev closing condition; no reviewer-completion claim. | — |

## Programme-level criteria (optional)

None. Focused Layout/regression batch: 119 passed; new integration file: 25 passed (22.59s); vocabulary tests: 58 passed. S0 passed with one declared group-header extent delta; inventory, annotations, vocabulary inventory, import direction and Scene delivery ownership checks pass. Independent review found no product defect; its SVG and legacy-byte evidence gaps were resolved in tests. Required next gates: adopt #1284's exact ready-main merge, publish one product PR, audit its exact-head artifacts/checks, then verify the final-review-containing main three-OS release. No local full pytest or authored corpus regeneration.
