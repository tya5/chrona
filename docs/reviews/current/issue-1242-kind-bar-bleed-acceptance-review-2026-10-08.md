# Kind bar bleed and bar-end stamp acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implementation through `c68b048b5ad3c5f1bd28ce07b4e5e00362f2f6a8`, based on
ready main `ba679506c1c8d4661004a480b704530830ea0488` (#1239).
Its bot-only report update changes no product code from the tested integration.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1242#issuecomment-6060806272).
Publication, exact-head CI/shared snapshot and exact published-main three-OS
release remain pending. Do not close yet.

## Literal issue acceptance

### Issue #1242

- Source: [Issue #1242](https://github.com/tya5/chrona/issues/1242)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | With `barBleed: border`, the bar's top, start and end edges equal the container's inner border edges, and the heading and body keep the declared inset from the border. | met | [Unequal per-side borders, inset text, fill/hug, actual SVG coordinates and PNG pixels](../../../tests/integration/test_annotation_kind_bar_bleed.py). | none |
| 2 | With `bar-end`, the stamp's end edge equals the bar's end edge, it lies within the bar's block extent, and no column is reserved. | met | [Completed bounds, label separation, body wrap/origins, wide and oversized glyphs, rotated local containment](../../../tests/integration/test_annotation_kind_bar_bleed.py). Actual role ink is visible in SVG/PNG and contrast is evaluated against the bar. | none |
| 3 | The defaults are byte-identical. | met | [Absent versus explicit none/column SVG and Scene surface bytes](../../../tests/integration/test_annotation_kind_bar_bleed.py); existing column kind-colour tests remain green. Shared public snapshot is still required. | none |
| 4 | Title Card adopts both (the owner's visual feedback). | deferred | Reviewer-owned adoption is explicitly not a dev closing condition on [board #454](https://github.com/tya5/chrona/issues/454); no authored examples changes here. | [Title Card #1182](https://github.com/tya5/chrona/issues/1182) |

## Programme-level criteria (optional)

Theme closes declarations; Layout measures the bar reserve before note search
and receives independent border/content bounds. Scene selects stamp role ink
for bar-end and retains legacy kind tint for column; it calculates no geometry.
Existing rotation and contrast paths are reused. Border bleed is an explicit
square-ended strip, including on rounded boxes; text retains corner clearance.
Actual corner pixels verify this selected treatment, not implicit clipping.
Combined annotation/Theme/Scene/ownership and heading-part regressions: 137 passed; schema
L1/L2/L3, annotations and literal acceptance checker passed. Public CI remains
pending. Generated outputs and examples were not authored.
