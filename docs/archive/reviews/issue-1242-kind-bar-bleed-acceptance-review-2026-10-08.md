# Kind bar bleed and bar-end stamp acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implemented in [PR #1245](https://github.com/tya5/chrona/pull/1245), merged as
[`8518c381aa08f0de61e16caab071edee90ab402d`](https://github.com/tya5/chrona/commit/8518c381aa08f0de61e16caab071edee90ab402d).
Final PR head [`ca5588d0020fbb036f7d5bbfed77ecc8ffd307c1`](https://github.com/tya5/chrona/commit/ca5588d0020fbb036f7d5bbfed77ecc8ffd307c1)
passed [PR CI run 37804848279](https://github.com/tya5/chrona/actions/runs/37804848279).
The exact published main containing the implementation and original literal acceptance table is
[`09572169c8b9f14614c7d6671f004a3ac0fdddda`](https://github.com/tya5/chrona/commit/09572169c8b9f14614c7d6671f004a3ac0fdddda);
[release run 37817234594](https://github.com/tya5/chrona/actions/runs/37817234594)
passed on that SHA (three-OS pytest/conformance/wheel smoke, MCP floor, and
newest-Python reproduction). The shared snapshot was artifact
[11562014485](https://github.com/tya5/chrona/actions/runs/37804848279), GitHub
artifact digest `sha256:309fdcb93035dd22c0265de4ad07af0c558e558f1b43442e3691532319c51fce`.
Its 145 before/after paths contained 68 SVGs and 68 Scene files with no adds,
removals, or SVG/Scene changes. The normalized inventory added only the two
guarded diagnostic sites; coverage added only the four declared enum values.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1242#issuecomment-6060806272).

## Literal issue acceptance

### Issue #1242

- Source: [Issue #1242](https://github.com/tya5/chrona/issues/1242)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | With `barBleed: border`, the bar's top, start and end edges equal the container's inner border edges, and the heading and body keep the declared inset from the border. | met | [Unequal per-side borders, inset text, fill/hug, actual SVG coordinates and PNG pixels](../../../tests/integration/test_annotation_kind_bar_bleed.py). | none |
| 2 | With `bar-end`, the stamp's end edge equals the bar's end edge, it lies within the bar's block extent, and no column is reserved. | met | [Completed bounds, label separation, body wrap/origins, wide and oversized glyphs, rotated local containment](../../../tests/integration/test_annotation_kind_bar_bleed.py). Actual role ink is visible in SVG/PNG and contrast is evaluated against the bar. | none |
| 3 | The defaults are byte-identical. | met | [Absent versus explicit none/column SVG and Scene surface bytes](../../../tests/integration/test_annotation_kind_bar_bleed.py); existing column kind-colour tests remain green. The exact-head shared snapshot above proves all 68 SVG and 68 Scene outputs unchanged. | none |
| 4 | Title Card adopts both (the owner's visual feedback). | deferred | Reviewer-owned adoption is explicitly not a dev closing condition on [board #454](https://github.com/tya5/chrona/issues/454); no authored examples changes here. | [Title Card #1182](https://github.com/tya5/chrona/issues/1182) |

## Programme-level criteria (optional)

Theme closes declarations; Layout measures the bar reserve before note search
and receives independent border/content bounds. Scene selects stamp role ink
for bar-end and retains legacy kind tint for column; it calculates no geometry.
Existing rotation and contrast paths are reused. Border bleed is an explicit
square-ended strip, including on rounded boxes; text retains corner clearance.
Actual corner pixels verify this selected treatment, not implicit clipping.
Combined annotation/Theme/Scene/ownership and heading-part regressions: 137
passed; schema L1/L2/L3, annotation checks, and the literal acceptance checker
passed. Generated outputs and examples were not authored. The final exact-main
release above supplies the publication and three-OS evidence.
