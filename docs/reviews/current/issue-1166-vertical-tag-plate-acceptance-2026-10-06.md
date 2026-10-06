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

[Final batch](https://github.com/tya5/chrona/pull/1173#issuecomment-6000139241):
all128 public SVG/Scene files are byte-identical; only two inventory/coverage
reports change. [Exact-main release](https://github.com/tya5/chrona/actions/runs/37356246084)
passed on `d43cc6beaf9d7589d2686faa3c0a4ed16cb249ff`, including three-OS
full pytest/conformance/wheel, MCP floor and newest-Python public materializers.

## Literal issue acceptance

### Issue #1166

- Source: [body](https://github.com/tya5/chrona/issues/1166)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The default and horizontal headers are byte-identical. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): omitted/explicit header completed primitives and SVG byte identity; existing horizontal group-tab regressions pass | — |
| 2 | With `tag`, there is one Rect per group spanning exactly its tag span, and the text lies inside it. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): three groups, CJK/rotated Latin, gaps0/4, exact inset spans/containment, actual SVG pattern/opacity and text contrast against the plate; [geometry guards](../../../tests/unit/chrona/presentation/layout/test_group_tab_geometry.py) | — |
| 3 | `tag` with a horizontal header is `E_THEME_TOKEN_TYPE`. | met | [Integration](../../../tests/integration/test_group_tag_plate.py): exact tabTarget pointer even with treatment none, plus all three forbidden header-geometry pointers | — |
| 4 | Yuya adopts it. | deferred | [Explicit reviewer disposition](https://github.com/tya5/chrona/issues/1166#issuecomment-6005941694): actual adoption is reviewer work, not a dev closing condition; synthetic support is not claimed as adoption | [#1116](https://github.com/tya5/chrona/issues/1116), [PR #1123](https://github.com/tya5/chrona/pull/1123) |

## Programme-level criteria (optional)

All synthetic rows are met; actual adoption is explicitly deferred to the
reviewer in #1116. Close after the exact-main release containing this review
update; the closure receipt records that run. No corpus resources are adapted.
