<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1821 rows 1 to 3

Observed on `main` at `734483472`. [Issue #1821](https://github.com/tya5/chrona/issues/1821) has three numbered `Acceptance:` rows. The body and its two comments (the reviewer's ownership note and the trial-15 note on the five designs) were re-fetched with `gh issue view 1821 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: three rows, none added since the issue was opened. Landed: [PR #1901](https://github.com/tya5/chrona/pull/1901) (`7e9307718`, owner-approved on the comparison page), which changes the Δ column of `designs/yuya`, `titlecard` and `sunday` to `format: signedDays`; its derived sync `1a62ce585` regenerated HALCYON-1 `22-yuya` and roadmap `roadmap-yuya`. The issue stays open: row 3 is narrowed until the render is recorded on the issue.

## Method

Venv inside a fresh worktree on `origin/main` `734483472` (`pip install -e '.[dev,render]' -e packages/chrona-fonts-noto-cjk`). Inputs are the trial-9 plan the #1790 review used, unchanged from [assets-1790](assets-1790/revised.yaml): `revised.yaml`, `baseline.yaml` and `actual.yaml`. The override Views are the output of `chrona preset copy yuya` with one line changed, shown as [views.diff](assets-1821/views.diff): `wording.keys: {delta.unit.workingDay: wd}` (or `営`), and, for the bar labels, `visibility.labels.placement: both` instead of the design's `table`. The script is [run.sh](assets-1821/run.sh) (all seven renders `status: ok`, [render.log](assets-1821/render.log)); the delta texts were read from each `--emit-scene` by Scene `purpose` with [summarize.py](assets-1821/summarize.py) into [texts.log](assets-1821/texts.log), and the PNGs were looked at. Focused tests: [pytest-1821.txt](assets-1821/pytest-1821.txt) (`test_finish_delta_unit_wording.py`, `test_preset_font_sets.py`, `test_ja_jp_builtin_wording.py`, `test_update_a_plan_guide_weekly_1870.py`, `test_locale_and_wording_guide.py`: 45 passed, none skipped). The full suite was not run.

## Literal issue acceptance

### Issue #1821

- Source: [Issue #1821](https://github.com/tya5/chrona/issues/1821)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | yuya's `facet.affixes` no longer carries a literal unit; the unit comes from `delta.unit.*` (en-US `+3d`, ja-JP `+3営業日`) or an affix that references a wording key. | met | [`designs/yuya/layout.yaml`](../../../src/chrona/resources/designs/yuya/layout.yaml) lines 77 to 83: the `facet` column style is `format: signedDays` with no `affixes` and no `日` anywhere in the file; `comparison.deltaUnit: working-days` (line 39) selects `delta.unit.workingDay`. Rendered with `--preset yuya` on the trial-9 plan: en-US table cells `+0d` … `+3d` … `+8d*` ([picture](assets-1821/yuya-en-US.png)), ja-JP `+3営業日` … `+8営業日*` ([picture](assets-1821/yuya-ja-JP.png)); counts per text in [texts.log](assets-1821/texts.log). Public evidence on `main`: HALCYON-1 [`22-yuya`](../../../examples/halcyon-1/generated/22-yuya.svg) and roadmap [`roadmap-yuya`](../../../examples/chrona-roadmap/generated/roadmap-yuya.svg) (both ja-JP) read `+3営業日`, `-6営業日` and `+0営業日` (22-yuya) and `+0営業日` (roadmap-yuya) in their Δ cells. | — |
| 2 | A `wording.keys` override of `delta.unit.workingDay` reaches yuya's table cells and bar labels. | met | With the yuya View plus `wording.keys: {delta.unit.workingDay: wd}`, en-US: every Δ table cell reads `+Nwd` (35 of 35: `+0wd` … `+8wd*`); with `営`, ja-JP: every cell reads `+N営` ([texts.log](assets-1821/texts.log)). The shipped yuya design places its labels in the table (`visibility.labels.placement: table`), so it draws no Δ on the bars at all; with `placement: both` the bar labels (Scene purpose `forecast-finish-delta`) appear and carry the override too, 35 of 35 `+Nwd` in en-US and `+N営` in ja-JP, identical to the table cells, while the same `placement: both` View without the override draws `+N営業日` on both in ja-JP ([en-US picture](assets-1821/yuya-en-US-override-both.png), [ja-JP picture](assets-1821/yuya-ja-JP-override-both.png), [view diffs](assets-1821/views.diff)). This is the route [`locale-and-wording.md`](../../guides/locale-and-wording.md) documents ("sets `wording.keys: {delta.unit.workingDay: 営}` … reaches the table cell, the label on the bar"). | — |
| 3 | A test or a render recorded on this issue shows yuya en-US and ja-JP. | narrowed | Renders exist: this review records yuya en-US (`+3d`) and ja-JP (`+3営業日`) as Scene texts and pictures ([en-US](assets-1821/yuya-en-US.png), [ja-JP](assets-1821/yuya-ja-JP.png), [log](assets-1821/render.log)). Neither is on the issue yet: its two comments carry no render, and no test asserts yuya's Δ unit in both locales (`test_preset_font_sets.py` renders yuya ja-JP for a font refusal; `test_finish_delta_unit_wording.py` uses a synthetic View, not yuya; both passed, [log](assets-1821/pytest-1821.txt)). The row becomes `met` once a comment on the issue links these two renders, which the closing comment can do. | [#1821](https://github.com/tya5/chrona/issues/1821) (comment linking the two renders) |

Counts: 3 rows, 2 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and the files under [assets-1821](assets-1821/render.log); it changes no code, schema, specification, guide, design or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of PR #1901 is in its own body and derived sync `1a62ce585`: HALCYON-1 21 target-b, 22 yuya, 23 titlecard, 25 sunday, and roadmap yuya, titlecard and sunday (Δ unit text; target-b note headers).
