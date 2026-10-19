<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1755 rows 1 to 3

Observed on `main` at `4760358c0`. [Issue #1755](https://github.com/tya5/chrona/issues/1755) has three acceptance rows. They landed through [PR #1762](https://github.com/tya5/chrona/pull/1762) (design note) and [PR #1766](https://github.com/tya5/chrona/pull/1766) (merge `526f9cfaa`: code, spec 06, `diagnostics.md`, tests). The issue body and all four comments were re-fetched with `gh issue view 1755 --json body,comments` on 2026-10-20 and counted literally: three numbered rows, none added since the first reading. Row 3 is the `diagnostics.md` row.

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, no shared install. The trial-8 inputs were extracted from the evidence branch commit `bf3940dbe` (`trial-8/w5/*` and `trial-8/looks/*`) into a temp directory and not committed. The synthetic plan is committed beside the pictures: [`project.yaml`](assets-1755-final/project.yaml) (kept and added), [`baseline.yaml`](assets-1755-final/baseline.yaml) (kept and dropped), [`actual.yaml`](assets-1755-final/actual.yaml). Tests run: `tests/unit/chrona/presentation/model/test_forecast_projection.py` (10 passed) and `tests/unit/chrona/skills/test_chrona_skill.py` (18 passed). The full suite was not run.

## Literal issue acceptance

### Issue #1755

- Source: [Issue #1755](https://github.com/tya5/chrona/issues/1755)
- Observed: 2026-10-20

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a baseline, plus one added and one removed task → forecast and baseline-compare render; the added task shows "new" and an empty Δ; the removed one appears as a removed ghost or in a diagnostic. | met | Baseline-compare, `chrona render project.yaml --preset target-b --snapshot baseline.yaml`: status `ok`, no error. Picture [synthetic-compare-target-b.png](assets-1755-final/synthetic-compare-target-b.png): "Added task" has `new` in the Δ finish column and no ahead/behind paint, and the row "Dropped task (removed)" is drawn as a dashed baseline ghost. Forecast, same command plus `--actual actual.yaml --forecast`: status `ok`, `I_FORECAST_MOVED` count 0, no `E_FORECAST_BASELINE_UNAVAILABLE`; picture [synthetic-forecast-target-b.png](assets-1755-final/synthetic-forecast-target-b.png) shows the same: "Kept task" `+0d*`, "Added task" `new` with a forecast bar, "Dropped task (removed)" as a ghost. The diagnostic branch: the same compare with the default preset (its View draws no ghosts) renders `ok` and lists `I_BASELINE_OBJECT_REMOVED`, "1 baseline objects have no current counterpart and no ghost is shown: Dropped task (gone)", with `objects: [{id: gone, title: Dropped task}]`. Tests (passed here) in [`test_forecast_projection.py`](../../../tests/unit/chrona/presentation/model/test_forecast_projection.py): `test_added_object_is_new_without_baseline_distance_and_removed_object_is_a_ghost_row` (finish delta text `new`, no delta value, `a` still `+1d`, ghost row `Gone (removed)`), `test_baseline_compare_without_forecast_marks_new_and_ghosts_removed_when_ghosts_are_on`, `test_removed_object_is_listed_when_the_view_hides_ghosts` and `test_removed_marker_survives_every_name_source` (title and path name sources). Rule in Spec [06](../../specification/06-view-model.md) and the design note [issue-1755](../../design/issue-1755-new-and-removed-objects-against-a-baseline-2026-10-19.md). Limit, not hidden: the markers are built-in English literals (`NEW_MARKER`, `REMOVED_MARKER` in [`projection.py`](../../../src/chrona/presentation/model/projection.py)), not wording keys as the reviewer's comment on the issue asked; the criterion names the words "new" and "removed", which are shown, so the row is met and the gap is filed as a successor to this row's marker text. | [#1781](https://github.com/tya5/chrona/issues/1781) |
| 2 | The trial-8 week-5 command renders with all three designs (PNG). | met | `chrona render trial-8/w5/project.yaml --preset trial-8/looks/<design>/preset.yaml --actual trial-8/w5/actual.yaml --snapshot trial-8/w5/baseline.yaml --forecast` (the issue's command with each design's preset) exits 0 with status `ok` and no diagnostics for all three. The issue observed `E_FORECAST_BASELINE_UNAVAILABLE: be-ratelimit`. PNGs: [executive-light](assets-1755-final/w5-executive-light.png), [target-b](assets-1755-final/w5-target-b.png), [marquee](assets-1755-final/w5-marquee.png). In the scene of each, `new` appears 4 times (Rate limiting and Deep link handling, the two tasks the issue named, each with delta and forecast cells) and the removed ghost "Cost guardrails (removed)" is present (target-b picture: Rate limiting `new`, Deep link handling `new`, last row "Cost guardrails (removed)" with its dashed baseline bar). | — |
| 3 | `diagnostics.md` covers `E_FORECAST_BASELINE_UNAVAILABLE`, in case it remains for a real failure. | met | [`skills/chrona/references/diagnostics.md`](../../../skills/chrona/references/diagnostics.md), section "Forecast and baseline comparison": a row for `E_FORECAST_BASELINE_UNAVAILABLE` (when it fires: a displayed object has no forecast schedule, or the baseline holds it as a different kind; a merely missing object is new; what to change), plus rows for `I_BASELINE_OBJECT_REMOVED` and the other forecast-path codes. The code remains for a real failure with a hint: [`test_forecast_without_a_schedule_for_a_displayed_object_still_refuses_with_a_hint`](../../../tests/unit/chrona/presentation/model/test_forecast_projection.py) (passed here) expects `E_FORECAST_BASELINE_UNAVAILABLE: b: the forecast has no schedule`. The skill reference tests ([`test_chrona_skill.py`](../../../tests/unit/chrona/skills/test_chrona_skill.py), 18 passed) pass with the new section. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds documents and pictures only.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review (one document, three week-5 pictures, two synthetic pictures, three small YAML inputs) | 0 | 0 | 0 | 0 |

The public effects of the reviewed PR #1766 are in its own body: new objects get an empty baseline delta with a `new` marker, removed objects get a ghost row marked `(removed)` or the new info diagnostic `I_BASELINE_OBJECT_REMOVED`, and `E_FORECAST_BASELINE_UNAVAILABLE` narrows to a displayed object without a forecast schedule. The decision record on the issue (comment 6255578052, with the reviewer's change 6255778812) is otherwise followed; the one divergence, English literal markers instead of wording keys, is [#1781](https://github.com/tya5/chrona/issues/1781).
