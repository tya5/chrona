<!-- chrona:literal-acceptance/v1 -->

# #1518: Packaged quarter/month axes

## Literal issue acceptance

### Issue #1518

- Source: [Issue #1518](https://github.com/tya5/chrona/issues/1518)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | an axis policy that admits a quarter band and a month band, each with its own labels, and short label forms for them. | met | [SVG regression](../../../tests/integration/test_packaged_quarter_month_axis.py): all three real renders show Q1–Q4 and Jan–Dec, 4 quarter and 12 month cells, aligned separate lanes, no axis/contrast warnings. | — |
| 2 | Change only the three packaged preset Views: a quarter band over a month band, with separate fixed-unit labels (`quarter`, `short-month`). | met | [Packaged Views](../../../src/chrona/resources/presets/bundles): technical-print, muted-executive and wallboard-dark; existing forms and `axisQuarter`/`axisMonth` typography, no core or schema change. | — |
| 3 | Add rendered preset regressions and correct the three gap reports. | met | SVG regression above; [technical-print](../../diagnostics/technical-print-vocabulary-gaps.md) row4, [muted-executive](../../diagnostics/muted-executive-vocabulary-gaps.md) row9 and [wallboard-dark](../../diagnostics/wallboard-dark-vocabulary-gaps.md) row3 updated. | — |
| 4 | Keep the other presets automatic. Heights, paint and borders stay Theme YAML tuning. | met | [Policy guard](../../../tests/unit/chrona/presentation/test_packaged_axis_auto_policy.py) checks every packaged/resolved builtin policy; other presets remain auto. No Theme file changes. | — |

## Programme-level criteria (optional)

## Architecture and release

Plan and architecture review: [approved work record](https://github.com/tya5/chrona/issues/1518#issuecomment-6185637929),
[reviewer decision](https://github.com/tya5/chrona/issues/1518#issuecomment-6185342573).
Specs39/63 already own independent measured lanes and finite forms; only View
declarations change. Reference pixel heights and white/hairline paint are author
tuning, not new core rules. Implementation: [417574bac](https://github.com/tya5/chrona/commit/417574bac192f4efe172254ba218096470d14cfc).
Policy, SVG, axis geometry and documentation tests: 58 passed. Independent
review found no blocking scope, ownership or adapter-evidence issue.
Final-head CI, public-materializer artifact review and the exact review-containing
main three-OS release remain required before closure.
