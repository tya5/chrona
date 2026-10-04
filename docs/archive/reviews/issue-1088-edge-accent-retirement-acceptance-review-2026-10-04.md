<!-- chrona:literal-acceptance/v1 -->
# Issue #1088 — border-only kind accent acceptance

Record: [archived design/review/plan](../planning/issue-1088-edge-accent-retirement-2026-10-04.md), Specifications 07/56.
Publication and grouped evidence: [PR #1144](https://github.com/tya5/chrona/pull/1144).

## Literal issue acceptance

### Issue #1088

- Source: [#1088](https://github.com/tya5/chrona/issues/1088)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | no corpus Theme declares edge | met | [All first-party Theme and derived-base contract checks](https://github.com/tya5/chrona/blob/35fde2fcae43e5ac8dc2b945c715a8e1064ece40/tests/unit/chrona/presentation/contracts/test_contract_resources.py); unused edge values removed too | — |
| 2 | the accent branch of the kind frame is gone | met | [Header/bar/stamp-only kind frame](https://github.com/tya5/chrona/blob/35fde2fcae43e5ac8dc2b945c715a8e1064ece40/src/chrona/presentation/layout/annotation_kind_frame.py), [outer-border coverage](https://github.com/tya5/chrona/blob/35fde2fcae43e5ac8dc2b945c715a8e1064ece40/tests/integration/test_annotation_border.py), [four-side header coverage](https://github.com/tya5/chrona/blob/35fde2fcae43e5ac8dc2b945c715a8e1064ece40/tests/integration/test_annotation_kind_header.py) | — |
| 3 | S0 gate and corpus diff reviewed | met | [S0 and 64-pair CI snapshot](https://github.com/tya5/chrona/actions/runs/37206049416), [grouped count/image review](https://github.com/tya5/chrona/pull/1144): only two SVGs and non-provenance Scenes change; 62 unaffected pairs identical; diagnostics unchanged, contrast errors 0 | — |

## Programme-level criteria (optional)

The two active Themes intentionally move their strip to the outer border.
Other SVG output must remain unchanged; Theme provenance identities change
with v0.15/v0.16. Layout alone owns border geometry; Scene/adapters are unchanged.
Closed on published main `35fde2fcae43e5ac8dc2b945c715a8e1064ece40` after the
[derived gate](https://github.com/tya5/chrona/actions/runs/37207649390) and
[three-OS, wheel and public-materializer release gate](https://github.com/tya5/chrona/actions/runs/37207799086) passed.
