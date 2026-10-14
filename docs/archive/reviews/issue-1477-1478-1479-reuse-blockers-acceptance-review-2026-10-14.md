# README reuse blockers acceptance review

<!-- chrona:literal-acceptance/v1 -->

Design/architecture/plans: issue Status records [1477](https://github.com/tya5/chrona/issues/1477#issuecomment-6158063296), [1479](https://github.com/tya5/chrona/issues/1479#issuecomment-6158063026).
Normative rules: pre-code1baf84d6 (Specs06/07) and the
[architecture correction](https://github.com/tya5/chrona/issues/1477#issuecomment-6158299823).
Layout owns role-specific wrapped geometry and the distinct inner-border bar
extent, without double-charging content insets; Scene/adapters remain unchanged.
The audit distinguishes Project content from design identity without weakening
resource admission. Both reviewer dispositions are approved:
[1477 replacement criterion](https://github.com/tya5/chrona/issues/1477#issuecomment-6167301301)
and [1479 shared-design scope](https://github.com/tya5/chrona/issues/1479#issuecomment-6162719463).
The independent #1478 title override is already released and closed; its
[archived acceptance review](../../archive/reviews/issue-1478-summary-panel-title-acceptance-review-2026-10-14.md)
is authoritative rather than a second acceptance table here.
Released in [PR1481](https://github.com/tya5/chrona/pull/1481), headbcf0a59c,
ready main930b82459d34c46b29e0e593c967d9e620ab8687.
[Containing-review release38568993335](https://github.com/tya5/chrona/actions/runs/38568993335)
PASS: all three OS full pytest/conformance/wheel-smoke, newest-Python public
materializers and MCP floor. Focused tests69PASS; review/ledger tests7PASS.
[Fresh public fixture evidence](https://github.com/tya5/chrona/pull/1481#issuecomment-6168807804)
uses immutable PR1476 sourcec2ddb68f. Snapshot11895911669 preserves101 paths,
90/92 visual files byte-identical; only the approved Yuya pair and its diagnostic
reports change. No authored examples or generated outputs edited.

## Literal issue acceptance

### Issue #1477

- Source: [issue](https://github.com/tya5/chrona/issues/1477)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Scene test: a 40-character kind title in a filled note wraps, and the canvas stays at the viewport. | met | [Filled-note tests](../../../tests/integration/test_filled_annotation_heading.py) prove title/secondary wrapping with independent role metrics, completed bar growth and actual SVG1600×900; content/forbid/unbreakable lines retain their behavior. | — |
| 2 | Target B, Title Card, Marquee and Sunday are byte-identical. HALCYON Yuya changes only where a title genuinely overflowed: the `Payload thermal-vacuum` note wraps to two lines inside its bar, with 16 primitives changed, 0 added or removed, and 2 overflow warnings removed. | met | [Approved replacement of the original five-design byte-identity row](https://github.com/tya5/chrona/issues/1477#issuecomment-6167301301), now applied to the issue body; [fresh batch evidence](https://github.com/tya5/chrona/pull/1481#issuecomment-6168807804). No compatibility exception. | — |
| 3 | PR #1476's roadmap-yuya renders at 1600 × 900. | met | Copied public PR1476 fixture:1626.172×900 before,1600×900 after; completed Scene and SVG viewBox agree. [Fresh evidence](https://github.com/tya5/chrona/pull/1481#issuecomment-6168807804). | — |
| 4 | Do not edit `examples/**`. | met | All fixture mutations and generated artifacts are outside the repository; [final source diff](https://github.com/tya5/chrona/compare/ac4ac88360708de5421baccf043f9e65c22f5e01...bcf0a59c9e341707d032b0020f8ee7fc12a56c98) has no examples paths. | — |

### Issue #1479

- Source: [issue](https://github.com/tya5/chrona/issues/1479)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The batch audit reports 0 findings over halcyon-1 and chrona-roadmap with PR #1476 applied. | met | Zero findings in reusable shared designs under `src/chrona/resources/designs/`, as [confirmed by the reviewer](https://github.com/tya5/chrona/issues/1479#issuecomment-6162719463). All67 legitimate findings in the three project-owned local HALCYON profiles remain reported, outside this criterion. [Fresh batch evidence](https://github.com/tya5/chrona/pull/1481#issuecomment-6168807804). | — |
| 2 | A planted project id in a design's text or binding is still reported. | met | [Purity tests](../../../tests/unit/tools/test_check_design_purity.py): Project id in Theme text and Summary `source.object` is detected; root format/identity and paint/token collisions are excluded.22 tests pass. | — |
| 3 | Do not edit `examples/**`. | met | Read-only audit and synthetic tests; source diff has no examples paths. [Evidence record](https://github.com/tya5/chrona/commit/b429eb7e). | — |

## Programme-level criteria (optional)

None.
