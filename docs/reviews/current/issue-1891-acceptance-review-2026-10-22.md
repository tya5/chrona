<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1891 rows 1 to 3

Observed on `main` at `b91f0f53c` (the derived-sync bot commit after [PR #1896](https://github.com/tya5/chrona/pull/1896)). [Issue #1891](https://github.com/tya5/chrona/issues/1891) has three numbered rows, each with one `Acceptance:` line. The body and its two comments (the row 2 design note and the reviewer's approval of the push-out rule, with "leave line-end prohibition for now") were re-fetched with `gh issue view 1891 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: three rows, no row added since the first reading. Row 1 landed in [PR #1893](https://github.com/tya5/chrona/pull/1893) (`1da06c47d`), row 2 in [PR #1894](https://github.com/tya5/chrona/pull/1894) (`f39a105fe`), row 3 in [PR #1895](https://github.com/tya5/chrona/pull/1895) (`3d3ff76fe`). All three rows are met; no reviewer-owned YAML is involved (PR #1895 states that no design YAML was needed).

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `origin/main` `b91f0f53c`, no shared install. Every log starts with the command it records. Focused tests: [pytest-1891.txt](assets-1891/pytest-1891.txt) (64 passed, none skipped; the full suite was not run). Two small scripts record the observations that the tests only assert: [`compare_font_routes.py`](assets-1891/compare_font_routes.py) and [`check_line_start.py`](assets-1891/check_line_start.py). The vertical-tag plans [`plan-lane-tags.yaml`](assets-1891/plan-lane-tags.yaml) and [`plan-lane-tags-tall.yaml`](assets-1891/plan-lane-tags-tall.yaml) are synthetic.

## Literal issue acceptance

### Issue #1891

- Source: [Issue #1891](https://github.com/tya5/chrona/issues/1891)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | for the same Project and preset, every render route (CLI render, materialize, MCP render_draft, render_workspace) resolves the same faces and emits the same font warnings. | met | The divergent route was `render_workspace` (and `chrona render-workspace`), which built its Draft without the preset's `resources.fontSets`; the guided closure now reads them through the same `_preset_font_metrics` as the ordinary Draft ([Spec 62](../../specification/62-declarative-presentation-packages.md), `closure.py`). Run here, with the CJK provider package absent and one installed CJK face named "Hiragino Sans" (the trial-16 situation), [the log](assets-1891/row1-font-routes.txt) shows `render_draft` and `render_workspace` emit identical `W_FONT_FAMILY_SKIPPED` lists for titlecard (27 notes) and yuya (20 notes), both starting with the `role=font-set` note; the regression test `test_render_workspace_resolves_the_preset_font_sets_like_render_draft` in [`test_preset_font_sets.py`](../../../tests/integration/test_preset_font_sets.py) passes ([log](assets-1891/pytest-1891.txt)). `chrona render` is `render_draft` (`_run_draft_render` in [`cli.py`](../../../src/chrona/app/cli.py)) and the MCP `render_draft` is the same use case. `chrona materialize` reads a Render Context rather than a preset: it expands the context's declared font set with the same `expand_font_set` and was brought to `render`'s font policy in #1842 row 3 ([`test_materialize_status_and_fonts.py`](../../../tests/integration/test_materialize_status_and_fonts.py), passing in the same log; [the #1842 review](issue-1842-acceptance-review-2026-10-21.md)). Not done: the materialize route was not run on one identical Project beside the other three, because its input is a manifest context rather than a preset. | — |
| 2 | under ja-JP, no wrapped line starts with a line-start-prohibited character (JIS X 4051 classes: small kana, closing brackets, 。、 and similar); synthetic note text tests each class. | met | The CJK break units keep a prohibited character with the preceding unit, so the break moves before that unit ([Spec 24](../../specification/24-table-timeline-presentation.md); the rule was approved on the issue; no setting, schema or diagnostic). [`test_line_start_prohibition.py`](../../../tests/unit/chrona/presentation/layout/test_line_start_prohibition.py) has one synthetic note per class (small hiragana and katakana, the long sound mark, closing corner bracket, parenthesis and lenticular bracket, full stop, comma, middle dot, colon, question and exclamation marks, iteration mark, wave dash, curly quote), wrapped at every width from one character to the full text ([log](assets-1891/pytest-1891.txt)). Beyond the test: [`check_line_start.py`](assets-1891/check_line_start.py) wraps text carrying each of the 77 characters of the test's prohibited set at every width, 1232 wraps, and finds 0 lines that start with one ([output](assets-1891/row2-line-start.txt)); the reported note 「設計レビュー」 wraps as `設計レ` / `ビュー`. Line-end prohibition (opening brackets) is unchanged, as the reviewer asked. | — |
| 3 | a vertical group tag whose text fits in the group's block size is not truncated; when it cannot fit, the diagnostic names the tag text. | met | The clear space no longer cuts a label that fits the rows (`vertical_text.py`, [Spec 07](../../specification/07-style-and-theme.md)), and the group-tag `W_LAYOUT_TEXT_ELLIPSIZED` carries the tag text as its subject. Tests `test_a_tag_that_fits_its_rows_is_not_cut_for_the_clear_space` and `test_a_cut_tag_names_its_text_in_the_warning` in [`test_vertical_writing.py`](../../../tests/integration/test_vertical_writing.py) pass. Run here with yuya under ja-JP ([log](assets-1891/row3-lane-tags.txt)): on the [tall plan](assets-1891/plan-lane-tags-tall.yaml) the tags `開発`, `QA・リリース` and `未割り当て` are drawn whole and no ellipsis warning is emitted ([SVG](assets-1891/plan-lane-tags-tall.svg)); on the [short plan](assets-1891/plan-lane-tags.yaml), where the two-row `QA・リリース` block is too small, the tag is cut to `Q…` and the warning reads "'QA・リリース' ... needs 15.225x67.3155, has 15.225x23.8" (and names `未割り当て` for the one-row lane) ([SVG](assets-1891/plan-lane-tags.svg)). | — |

Counts: 3 rows, 3 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, logs, two scripts, two synthetic plans and two SVG renders under [assets-1891](assets-1891/pytest-1891.txt); it changes no code, schema, specification, guide, preset or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PRs is in their own bodies (PR #1895: one of 50 public slides, `chrona-roadmap/roadmap-yuya`, where the `rc` tag now fits).
