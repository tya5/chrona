<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — visual leftovers from #882 and #588

Current [work record](https://github.com/tya5/chrona/issues/988#issuecomment-6158930035).
Evidence baseline: READY1299e952a22d855f81d04f32b5ad81ff0f462da8.
Reviewer [rescope](https://github.com/tya5/chrona/issues/988#issuecomment-6091098524)
replaces deleted group-tabs with Title Card; its tab aspect is
[already accepted](https://github.com/tya5/chrona/issues/988#issuecomment-6105917331).
This issue needs no product change or examples edit. Existing affix/tab focused
tests:55 passed. PNGs rasterize exact committed SVGs at96dpi with resvg-py0.5.0 /
resvg0.48.1, only the packaged fonts matching Scene's font identities, no host fonts.
Closed after containing-review exact-main [release38501977990](https://github.com/tya5/chrona/actions/runs/38501977990)
passed all three OSes on f0d6fa73dc4dda98f690c7256ae29477cfcde5cb.

## Literal issue acceptance

### Issue #988

- Source: [Issue #988](https://github.com/tya5/chrona/issues/988)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Item 1: the group tab's aspect ratio; check that `tabInlineSize` and `tabBlockSize` can express the target, and set them in the target YAML (#987); if not, file the missing knob. | met | Reviewer rescope/acceptance above; all six Title Card tabs are14×20px. [Current SVG](https://github.com/tya5/chrona/blob/1299e952a22d855f81d04f32b5ad81ff0f462da8/examples/halcyon-1/generated/23-titlecard.svg), [PNG](../evidence/issue-988-2026-10-14/titlecard.png), and [general knob tests](../../../tests/integration/test_group_tab.py). No missing knob. | — |
| 2 | Item 2: the quarter and month labels on `group-tabs` collide (`2026 Q1 / Mar`) and the row spacing is loose; fix the YAML, or the rule with a synthetic test. | met | Reviewer rescope targets Title Card. [Its PNG](../evidence/issue-988-2026-10-14/titlecard.png) has no collision or loose tier spacing: quarter bounds end at193.975, month bounds start197.85, positive gap3.875px; tabs occupy the separate table start. No general rule defect or YAML change is needed. | — |
| 3 | Item 3: on `value-affixes` the affix renders as `+4 !` with a gap; make the affix join flush by default or offer a declared gap defaulting to 0. | met | The current region-frames Context uses the value-affixes View: [SVG](https://github.com/tya5/chrona/blob/1299e952a22d855f81d04f32b5ad81ff0f462da8/examples/controller-z/generated/region-frames.svg), [PNG](../evidence/issue-988-2026-10-14/region-frames.png) show +4! and ?. [Normalization](../../../src/chrona/presentation/review/v05_content.py) concatenates prefix/core/suffix once with no inserted gap; [synthetic state/measurement tests](../../../tests/integration/test_table_affixes_render.py) pin that general rule. | — |
| 4 | Each item is fixed or explained, with PNG evidence. | met | All three items are explained above using actual public output: [Title Card PNG](../evidence/issue-988-2026-10-14/titlecard.png) and [region-frames PNG](../evidence/issue-988-2026-10-14/region-frames.png). Both were visually reviewed. Source SVG SHA256:3b03af4dae4ad35404d437578fedece7ee60f685da26d2aec161b8a721632640 /14c5cd829003d7072aeac730f7167aa02b915379a699b8e07b93dbc63a7bf460. | — |

## Programme-level criteria (optional)

None.
