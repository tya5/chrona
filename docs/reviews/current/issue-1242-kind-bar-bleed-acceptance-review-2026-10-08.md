# Kind bar bleed and bar-end stamp acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implementation includes frozen-vocabulary registration `179a3abe6c67b303335ca9662cc60b9a9ee74ff0`, based on
ready main `dab0bb3b419e41b2aee95e470d74e6296718eb27` (#1239 and reviewer PR1241).
The public-base merge preserves the reviewer's YAML and bot-generated evidence.
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

PR run [37794966428](https://github.com/tya5/chrona/actions/runs/37794966428)
failed only `test_vocabulary_is_a_registered_live_part_with_frozen_digests`
(shard 3: 2728 passed); `derived-ready` consequently rejected its pytest
outcome. The two new vocabulary definitions lacked Spec56 frozen inventory
digests. Registering both definitions changes neither their schemas nor
runtime behavior; all 81 vocabulary/inventory tests now pass. Reviewer PR1241's
three Title Card YAML changes were ordinary-merged without product conflicts.
The updated-base L1/L2/L3 schema equivalence check passed (L2+L3 40.9s),
as did another 96 vocabulary/parts/annotation tests. Exact-head CI and shared
snapshot must be refreshed on this ready published main before merge.
