<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1781 rows 1 to 3

Observed on `main` at `e9aeef54e`. [Issue #1781](https://github.com/tya5/chrona/issues/1781) has three acceptance rows. They landed through [PR #1798](https://github.com/tya5/chrona/pull/1798) (merge `114291014`: code, wording table, Spec 06 and 63, tests). The issue body and comments were re-fetched with `gh issue view 1781 -R tya5/chrona --json body,comments` on 2026-10-21 and counted literally: three numbered rows, no comments, none added since the first reading.

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, CJK fonts installed, no shared install. The synthetic added-and-removed plan is the one of the #1755 review, copied beside the pictures: [`project.yaml`](assets-1781/project.yaml) (kept and added), [`baseline.yaml`](assets-1781/baseline.yaml) (kept and dropped), [`actual.yaml`](assets-1781/actual.yaml). Commands: `chrona render project.yaml --preset target-b --snapshot baseline.yaml [--actual actual.yaml --forecast] --locale <l>`. Tests run: `tests/integration/test_baseline_marker_wording.py` (2 tests), `tests/unit/chrona/presentation/model/test_forecast_projection.py`, `tests/unit/chrona/presentation/model/test_wording_tables.py` and `tests/unit/chrona/usecases/test_source_profile_validation.py` (37 passed together). The full suite was not run.

## Literal issue acceptance

### Issue #1781

- Source: [Issue #1781](https://github.com/tya5/chrona/issues/1781)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `wording-tables-v0.1.yaml` has en-US and ja-JP entries for the new marker and the removed marker (suggested keys `marker.baselineNew`, `marker.baselineRemoved`), resolved through `WordingResolver` (View `wording` overrides apply). | met | [`wording-tables-v0.1.yaml`](../../../src/chrona/resources/wording-tables-v0.1.yaml) holds `marker.baselineNew` and `marker.baselineRemoved` in both tables: en-US `new` and `removed`, ja-JP `新規` and `削除`. The code reads them through the resolver (`projection.py`), no longer from `NEW_MARKER` and `REMOVED_MARKER` literals. The View override: [`test_baseline_marker_wording.py`](../../../tests/integration/test_baseline_marker_wording.py) `test_markers_follow_the_locale_and_view_wording_keys_override` (passed here). Key lists: [`test_wording_tables.py`](../../../tests/unit/chrona/presentation/model/test_wording_tables.py) (both locales complete, no Japanese entry repeats the English text). | — |
| 2 | The ghost title composes the localized removed marker; the `path` and `title` name sources both carry it. | met | ja-JP baseline compare, `chrona render project.yaml --preset target-b --snapshot baseline.yaml --locale ja-JP`: the ghost row reads `Dropped task (削除)` ([compare-ja-JP.png](assets-1781/compare-target-b-ja-JP.png), [svg](assets-1781/compare-target-b-ja-JP.svg), status `ok` in [json](assets-1781/compare-target-b-ja-JP.json)); en-US reads `Dropped task (removed)` ([compare-en-US.png](assets-1781/compare-target-b-en-US.png)). On the trial-9 revised plan under `--locale ja-JP` (target-b with the forecast), the `path` name source reads `リリース準備 / プレスリリース準備 (削除)` ([picture](assets-1790/delta-target-b-ja-JP.png)). Both name sources carry the marker because the localized text is composed into the ghost title itself, which every name source starts from: [`test_markers_follow_the_locale_and_view_wording_keys_override`](../../../tests/integration/test_baseline_marker_wording.py) asserts the ja-JP ghost title `Dropped task (削除)` and the override `Dropped task (gone)`, and the existing [`test_removed_marker_survives_every_name_source`](../../../tests/unit/chrona/presentation/model/test_forecast_projection.py) asserts the `title` and `path` sources end with the marker (en-US; both passed here). Limit, not hidden: no test reads the `path` source under ja-JP; that case is shown by the picture above only. | — |
| 3 | A test renders the synthetic added-and-removed plan with `locale: ja-JP` and asserts both Japanese markers; the en-US outputs are unchanged. | met | [`test_ja_jp_render_shows_both_japanese_markers_and_en_us_is_unchanged`](../../../tests/integration/test_baseline_marker_wording.py) (passed here) renders the plan in ja-JP and asserts `新規` and `削除`, and compares en-US with the former text. The same two words in the rendered picture, forecast with `--actual actual.yaml --forecast --locale ja-JP`: the added row reads `新規` in the finish-delta column and the ghost reads `Dropped task (削除)` ([forecast-ja-JP.png](assets-1781/forecast-target-b-ja-JP.png), [svg](assets-1781/forecast-target-b-ja-JP.svg)). en-US, same command: `new` and `Dropped task (removed)` ([forecast-en-US.png](assets-1781/forecast-target-b-en-US.png)), matching the #1755 review's pictures. Row titles `Kept task`, `Added task`, `Dropped task` are authored text and stay as written. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds documents and pictures only.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review (one document, four pictures, their SVG and JSON, three small YAML inputs) | 0 | 0 | 0 | 0 |

The public effect of the reviewed PR #1798 is in its own body: under `--locale ja-JP` the baseline markers read `新規` and `(削除)` instead of `new` and `(removed)`; en-US output is unchanged.
