<!-- chrona:literal-acceptance/v1 -->

# Empty annotation and legend source allocation

Public base `66bf64325`; implementation `aa3daa47e`, reconciled at `2f8c50b2d`.
[Design, architecture corrections and implementation plan](https://github.com/tya5/chrona/issues/1597#issuecomment-6219156120).
Final-head CI, BOT byte-audit refresh and exact review-containing main three-OS
release remain required before closure.

## Literal issue acceptance

### Issue #1597

- Source: [Issue #1597](https://github.com/tya5/chrona/issues/1597)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: rail with notes keeps its width; rail without notes gives the width to the plot. | met | [Source-presence integration](../../../tests/integration/test_annotation_slot_presence.py): populated300px rail retained, empty/filtered/hidden removed, literal View note retained, required empty sources validated then omitted, empty/nonempty side legend. [Measurement controls](../../../tests/unit/chrona/usecases/test_annotation_source_measurement.py) prove typed zero measurement without unused annotation typography. Focused batches36 and67 passed. | — |
| 2 | The #1582 CSV in the four presets fills the canvas width, viewed as PNG. | met | Root viewed all four final PNGs in `/private/tmp/chrona-1597-final-png.cpFMDd/`, using the exact [#1582 CSV](https://github.com/tya5/chrona/issues/1582). Plot right edges: target-b1572, marquee1562, yuya1558, sunday1560 within each design's authored frame padding. First three no longer reserve empty rails; Sunday was already a passing no-rail control. No Project/preset tuning. | — |
| 3 | Public SVG/Scene byte-identical (all committed preset slides have notes); otherwise changes listed with counts. | met | Official `tools.derived_workflow snapshot 66bf64325` completed:109 before/after paths,0 added/retired, all50 SVG byte-identical. Three Scenes listed below remove one empty source slot each; all primitives and diagnostics remain identical. Other47 Scenes byte-identical; two reports change. Counts are disclosed with the [work record](https://github.com/tya5/chrona/issues/1597#issuecomment-6219156120) and PR. | — |

| Context | SVG changes | Scene slots removed | Primitive/route/diagnostic changes |
| --- | ---: | ---: | ---: |
| controller-z/plan-only | 0 | 1 | 0 |
| halcyon-1/04-tvac-slip | 0 | 1 | 0 |
| halcyon-1/07-replan-baseline | 0 | 1 | 0 |

## Programme-level criteria (optional)

Layout preserves typed source availability through validation and zero-content
measurement, then reuses semantic-absence tree normalization and stable-ID path
remapping before allocation. Empty source subtrees have no frame/caption placement
notice; content-present placement, suppression and error rules are unchanged.
Core, View selection, Scene and adapters are unchanged. Specs08/33 are aligned;
independent architecture review found no remaining blocker. Generated evidence
is not authored or committed by this PR.
