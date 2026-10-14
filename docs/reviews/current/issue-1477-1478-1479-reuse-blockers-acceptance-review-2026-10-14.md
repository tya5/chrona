# README reuse blockers acceptance review

<!-- chrona:literal-acceptance/v1 -->

Design/architecture/plans: issue Status records [1477](https://github.com/tya5/chrona/issues/1477#issuecomment-6158063296), [1479](https://github.com/tya5/chrona/issues/1479#issuecomment-6158063026).
Normative rules published before code in1baf84d6 (Specs06/07). View closes wording;
Layout completes role-specific wrapped geometry; Scene/adapters remain unchanged.
The audit distinguishes Project content from design identity, without weakening
resource admission. Schema description-only change: equivalence PASS, all38
structural fingerprints unchanged, corpus/diagnostic probes unchanged.
Public PR1476 fixture baseline:c2ddb68f. Rendering uses isolated copies; no tracked
example or generated evidence is edited. Current-head CI and containing-review
three-OS release are required before closure. Both reviewer dispositions are approved:
[1477 replacement criterion](https://github.com/tya5/chrona/issues/1477#issuecomment-6167301301)
and [1479 shared-design scope](https://github.com/tya5/chrona/issues/1479#issuecomment-6162719463).
The independent #1478 title override is already released and closed; its
[archived acceptance review](../../archive/reviews/issue-1478-summary-panel-title-acceptance-review-2026-10-14.md)
is authoritative rather than a second acceptance table here.
Current public base: ac4ac88360708de5421baccf043f9e65c22f5e01 (trusted derived-main success).
After normal main adoption, 69 focused tests pass; public fixture evidence is
being refreshed before the final PR push. Counts below identify the prior
fixture batch, not a new current-head release gate.
Focused integrated verification:126 tests passed (43.28s); review/closed-ledger
tests7 passed. Final five-design batch preserves4 complete Scene/SVG pairs;
only Yuya changes as disclosed below. Both roadmap canvases are1600×900.
The [pre-code architecture correction](https://github.com/tya5/chrona/issues/1477#issuecomment-6158299823)
closes Spec07/#1242's distinct inner-border bar extent: the bar may use width
beyond content insets, without charging that extension twice to note size.
[Bleed regressions](../../../tests/integration/test_annotation_kind_bar_bleed.py)
check fitting/wrapped role text, unchanged inset heading/body and actual SVG.

## Literal issue acceptance

### Issue #1477

- Source: [issue](https://github.com/tya5/chrona/issues/1477)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Scene test: a 40-character kind title in a filled note wraps, and the canvas stays at the viewport. | met | [Filled-note tests](../../../tests/integration/test_filled_annotation_heading.py) prove title/secondary wrapping with independent role metrics, completed bar growth and actual SVG1600×900; content/forbid/unbreakable lines retain their behavior. | — |
| 2 | Target B, Title Card, Marquee and Sunday are byte-identical. HALCYON Yuya changes only where a title genuinely overflowed: the `Payload thermal-vacuum` note wraps to two lines inside its bar, with 16 primitives changed, 0 added or removed, and 2 overflow warnings removed. | met | [Approved replacement of the original five-design byte-identity row](https://github.com/tya5/chrona/issues/1477#issuecomment-6167301301), independently rendered by the reviewer; [batch evidence](https://github.com/tya5/chrona/issues/1477#issuecomment-6158140898). No compatibility exception. | — |
| 3 | PR #1476's roadmap-yuya renders at 1600 × 900. | met | Actual copied PR1476 public materializer:1626.172×900 before,1600×900 after; completed Scene and SVG viewBox agree. [Evidence record](https://github.com/tya5/chrona/issues/1477#issuecomment-6158140898). | — |
| 4 | Do not edit `examples/**`. | met | All fixture mutations and generated artifacts are outside the repository; source diff has no examples paths. [Evidence record](https://github.com/tya5/chrona/compare/85ed35f1...dev-a%2Freadme-reuse-blockers-20261014). | — |

### Issue #1479

- Source: [issue](https://github.com/tya5/chrona/issues/1479)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The batch audit reports 0 findings over halcyon-1 and chrona-roadmap with PR #1476 applied. | met | Zero findings in reusable shared designs under `src/chrona/resources/designs/`, as [confirmed by the reviewer](https://github.com/tya5/chrona/issues/1479#issuecomment-6162719463). Legitimate findings in the three project-owned local HALCYON profiles remain reported; they are outside this criterion. [Batch evidence](https://github.com/tya5/chrona/issues/1479#issuecomment-6158115188). | — |
| 2 | A planted project id in a design's text or binding is still reported. | met | [Purity tests](../../../tests/unit/tools/test_check_design_purity.py): Project id in Theme text and Summary `source.object` is detected; root format/identity and paint/token collisions are excluded.22 tests pass. | — |
| 3 | Do not edit `examples/**`. | met | Read-only audit and synthetic tests; source diff has no examples paths. [Evidence record](https://github.com/tya5/chrona/commit/b429eb7e). | — |

## Programme-level criteria (optional)

None.
