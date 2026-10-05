<!-- chrona:literal-acceptance/v1 -->
# Issue #1166 — vertical tag plates

Public ready-main base: `c917b718d883b20774dcefbfafe4760b1a677da6`
([exact-SHA gate](https://github.com/tya5/chrona/actions/runs/37349443335)).
[Current plan/publication receipts](https://github.com/tya5/chrona/issues/1166#issuecomment-5998782451).
Layout shares one completed gap-inset cell between text and plate; Theme selects
the target/paint, Scene and adapters keep their existing projection contracts.
Independent architecture review found no ownership or default-behavior breach.

Focused verification: 174 group-tab, vertical-text, synthetic tag-plate and
capability/consumer tests passed. Schema equivalence passed (L1 additive1/equal37;
L2/L3 no new invalid fixtures). Its pruning tool retired only the two already
merged R6 Scene delta records. No examples or generated files are edited.
Packaged-font resvg review of the actual gap4 synthetic SVG confirms that all
three plates contain upright CJK and rotated Latin without clipping/overlap;
the adjacent row labels stay outside their tag columns.

## Literal issue acceptance

### Issue #1166

- Source: [body](https://github.com/tya5/chrona/issues/1166)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The default and horizontal headers are byte-identical. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): omitted/explicit header completed primitives and SVG byte identity; existing horizontal group-tab regressions pass | — |
| 2 | With `tag`, there is one Rect per group spanning exactly its tag span, and the text lies inside it. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): three groups, CJK/rotated Latin, gaps0/4, exact inset spans/containment, actual SVG pattern/opacity and text contrast against the plate; [geometry guards](../../../tests/unit/chrona/presentation/layout/test_group_tab_geometry.py) | — |
| 3 | `tag` with a horizontal header is `E_THEME_TOKEN_TYPE`. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): exact tabTarget pointer even with treatment none, plus all three forbidden header-geometry pointers | — |
| 4 | Yuya adopts it. | not met | [Reviewer-owned target #1116](https://github.com/tya5/chrona/issues/1116)/[PR #1123](https://github.com/tya5/chrona/pull/1123); synthetic support does not prove actual adoption | — |

## Programme-level criteria (optional)

Keep open until actual Yuya adoption, reviewed final-head shared corpus/visible
output, all required PR checks and exact-main three-OS release are verified.
There are no existing public tabTarget declarations; disclose actual CI counts
rather than adapting the corpus or treating that inventory as byte evidence.
