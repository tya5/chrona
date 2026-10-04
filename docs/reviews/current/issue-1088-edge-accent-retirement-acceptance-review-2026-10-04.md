<!-- chrona:literal-acceptance/v1 -->
# Issue #1088 — border-only kind accent acceptance

Authority: [current design/review/plan](../../planning/active/issue-1088-edge-accent-retirement-2026-10-04.md), Specifications 07/56.
Publication and grouped evidence: [PR #1144](https://github.com/tya5/chrona/pull/1144).

## Literal issue acceptance

### Issue #1088

- Source: [#1088](https://github.com/tya5/chrona/issues/1088)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | no corpus Theme declares edge | met | [All first-party Theme and derived-base contract checks](../../../tests/unit/chrona/presentation/contracts/test_contract_resources.py); unused edge values removed too | — |
| 2 | the accent branch of the kind frame is gone | met | [Header/bar/stamp-only kind frame](../../../src/chrona/presentation/layout/annotation_kind_frame.py), [outer-border coverage](../../../tests/integration/test_annotation_border.py), [four-side header coverage](../../../tests/integration/test_annotation_kind_header.py) | — |
| 3 | S0 gate and corpus diff reviewed | not met | [PR #1144](https://github.com/tya5/chrona/pull/1144): S0 and grouped Scene/SVG/image evidence remain required before merge | — |

## Programme-level criteria (optional)

The two active Themes intentionally move their strip to the outer border.
Other SVG output must remain unchanged; Theme provenance identities change
with v0.15/v0.16. Layout alone owns border geometry; Scene/adapters are unchanged.
Close only after the exact published review-containing three-OS, wheel and
public-materializer release gate succeeds; cite that run in the closing comment.
