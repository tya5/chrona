# README reuse blockers acceptance review

<!-- chrona:literal-acceptance/v1 -->

Design/architecture/plans: issue Status records [1477](https://github.com/tya5/chrona/issues/1477#issuecomment-6158063296), [1478](https://github.com/tya5/chrona/issues/1478#issuecomment-6158063569), [1479](https://github.com/tya5/chrona/issues/1479#issuecomment-6158063026).
Normative rules published before code in1baf84d6 (Specs06/07). View closes wording;
Layout completes role-specific wrapped geometry; Scene/adapters remain unchanged.
The audit distinguishes Project content from design identity, without weakening
resource admission. Schema description-only change: equivalence PASS, all38
structural fingerprints unchanged, corpus/diagnostic probes unchanged.
Public PR1476 fixture baseline:c2ddb68f. Rendering uses isolated copies; no tracked
example or generated evidence is edited. Current-head CI and containing-review
three-OS release are required before closure. Two literal dispositions remain open.
Focused integrated verification:124 tests passed (42.29s); review/closed-ledger
tests7 passed. Final five-design batch preserves4 complete Scene/SVG pairs;
only Yuya changes as disclosed below. Both roadmap canvases are1600×900.

## Literal issue acceptance

### Issue #1477

- Source: [issue](https://github.com/tya5/chrona/issues/1477)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Scene test: a 40-character kind title in a filled note wraps, and the canvas stays at the viewport. | met | [Filled-note tests](../../../tests/integration/test_filled_annotation_heading.py) prove title/secondary wrapping with independent role metrics, completed bar growth and actual SVG1600×900; content/forbid/unbreakable lines retain their behavior. | — |
| 2 | The five halcyon designs are byte-identical: their titles fit today. | not met | [Measured conflict](https://github.com/tya5/chrona/issues/1477#issuecomment-6158140898): Yuya's title199.776px exceeds its193.8px available bar content. General wrapping changes its16 primitives, removes2 overflow warnings and adds/removes no primitives. No project-specific exception. Owner disposition is required. Fitting-string whitespace normalization was corrected. | — |
| 3 | PR #1476's roadmap-yuya renders at 1600 × 900. | met | Actual copied PR1476 public materializer:1626.172×900 before,1600×900 after; completed Scene and SVG viewBox agree. [Evidence record](https://github.com/tya5/chrona/issues/1477#issuecomment-6158140898). | — |
| 4 | Do not edit `examples/**`. | met | All fixture mutations and generated artifacts are outside the repository; source diff has no examples paths. [Evidence record](https://github.com/tya5/chrona/compare/85ed35f1...dev-a%2Freadme-reuse-blockers-20261014). | — |

### Issue #1478

- Source: [issue](https://github.com/tya5/chrona/issues/1478)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The halcyon Title Card is byte-identical. | met | With no wording override, the resolver preserves panel title, metric content and authored profile identity. The final materializer comparison checks full Scene/SVG bytes against the baseline; the independent fitting-text correction preserves the authored spaces. [Evidence record](https://github.com/tya5/chrona/issues/1478#issuecomment-6158214974). | — |
| 2 | PR #1476's roadmap Title Card can read e.g. `RC まで`. | met | A copied PR1476 View overrides `countdown.title`; actual Scene primitive `summary:/panels/0/title` and serialized SVG text both read `RC まで`, canvas1600×900. The shared design is unchanged. [Evidence record](https://github.com/tya5/chrona/issues/1478#issuecomment-6158214974). | — |
| 3 | Test for override and for an unknown panel. | met | [Profile connection tests](../../../tests/unit/chrona/presentation/review/test_profile_connections.py): exact joined title selector, immutable original profile, escaped unknown pointer, metric/title and duplicate-panel ambiguity;13 tests pass. | — |
| 4 | Do not edit `examples/**`. | met | Source diff has no examples paths. Only disposable fixture Views are changed for evidence. [Evidence record](https://github.com/tya5/chrona/commit/bf6e96a8). | — |

### Issue #1479

- Source: [issue](https://github.com/tya5/chrona/issues/1479)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The batch audit reports 0 findings over halcyon-1 and chrona-roadmap with PR #1476 applied. | not met | Actual batch has zero shared-design findings and no input/reference errors, eliminating22 false positives. It correctly retains67 findings in3 legacy project-specific local HALCYON profiles. [Scope clarification requested](https://github.com/tya5/chrona/issues/1479#issuecomment-6158115188); do not suppress legitimate leaks to satisfy an ambiguous count. | — |
| 2 | A planted project id in a design's text or binding is still reported. | met | [Purity tests](../../../tests/unit/tools/test_check_design_purity.py): Project id in Theme text and Summary `source.object` is detected; root format/identity and paint/token collisions are excluded.22 tests pass. | — |
| 3 | Do not edit `examples/**`. | met | Read-only audit and synthetic tests; source diff has no examples paths. [Evidence record](https://github.com/tya5/chrona/commit/b429eb7e). | — |

## Programme-level criteria (optional)

None.
