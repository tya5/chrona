# Design Plan — PR pytest speed and balance (#657)

**Status:** Design plan (this file), design, review and implementation plan published together as I657-0.
**Design:** [design](../../design/issue-657-pr-pytest-speed-design-2026-09-30.md)
**Review:** [architecture review](../../reviews/current/issue-657-pr-pytest-speed-architecture-review-2026-09-30.md)
**Implementation plan:** [implementation plan](issue-657-pr-pytest-speed-implementation-plan-2026-09-30.md)
**Related:** #555 (CI paths), #575 (synthetic tests instead of corpus), #573, #590.

## Literal acceptance (copied from the issue)

| # | Criterion |
| --- | --- |
| 1 | PR-path pytest wall-clock time (the slowest shard) is under about 150 s on a code PR, and the shards are within about 20% of each other. |
| 2 | Each (project, preset) combination is rendered at most once per test session in the PR path. A test asserts this through the fixture's render counter. |
| 3 | No test coverage is lost: every rule tested before still has a PR-path test (synthetic where it was HALCYON-only); `corpus`-marked tests run on main, nightly and manual runs; the full suite still passes on those runs. |
| 4 | `.test_durations` is committed and refreshed by an automated job, and AGENTS.md says how. |

## Published baseline (`main` at `400f323d`, verified 2026-09-30)

- `.github/workflows/conformance.yml`, job `pr-pytest`: three Ubuntu shards, `pytest -n 4 --splits 3 --group N --splitting-algorithm least_duration`, on code PRs only. Docs-only PRs skip it (`tools/classify_ci_change.py`).
- `reproduction-newest-python` (Python 3.12) also runs `tests/integration/test_materialize_example.py::test_declared_examples_reproduce_by_public_cli` on every code PR, by node id and with no marker filter.
- The `full-matrix` job (three OS, `pytest -n 4`, no marker filter) runs on `schedule` (04:00 UTC), `workflow_dispatch`, and the post-sync dispatch after each push to `main`.
- pytest-split reads `.test_durations` from the repository root by default, so committing the file needs **no workflow change**. The file does not exist today, so `least_duration` splits by test count. `pytest-split` is in the `dev` extra.
- `pyproject.toml` has `[tool.pytest.ini_options] testpaths = ["tests"]` only: no markers, no `addopts`. There is no `conftest.py` and no `tests/support/`.

## Measurement (CI hardware, not the inflated local numbers)

The issue's local table came from an 8-way parallel run and a machine under heavy load (load average 200 to 300 while I measured, other agents), so it only ranks tests. Two CI sources were used.

**A. Shard wall-clock, six recent code-PR runs** (step "Run pytest", seconds; shard 1 / 2 / 3):

| Run | 1 | 2 | 3 | slowest / fastest |
| --- | --- | --- | --- | --- |
| 36722028954 (I574-3) | 220 | 333 | 91 | 3.7x |
| 36719001713 (I574-2) | 280 | 219 | 246 | 1.3x |
| 36715476473 (I574-1, the issue's run) | 399 | 148 | 236 | 2.7x |
| 36665050632 (I592-6) | 209 | 222 | 373 | 1.8x |
| 36662657708 (I592-5b) | 216 | 416 | 231 | 1.9x |
| 36660187428 (I592-5a) | 231 | 157 | 340 | 2.2x |

The slowest shard was 280 to 416 s (median about 355 s), and which shard is slowest changes from run to run, because count-based splitting reshuffles with every added test. The three shards sum to 644 to 863 s. Shard job time is the pytest step plus about 20 s of install and snapshot apply.

**B. Per-test durations on CI** (run 36724348189 on a throwaway branch whose `addopts` printed `--durations=0 --durations-min=0`; PR 661, closed unmerged). Setup, call and teardown are summed per test; 1858 tests, 1745 worker-seconds in total (shards 768 / 633 / 343 worker-seconds, wall-clock 303 / 276 / 149 s per job):

| Worker s | Tests | What |
| --- | --- | --- |
| 201.5 | 1 | `test_readable_defaults.py::test_default_draft_and_presets_draw_a_distinct_axis_band`: default plus 7 presets in one test, so about 25 s per render and undistributable |
| 309.8 | 9 | `test_axis_cells.py`: 7 catalogue presets on HALCYON with actuals (28 to 56 s each) plus `test_start_aligned_month_labels…` (28 s, mission-light again) |
| 342.7 | 7 | `test_cli.py::test_cli_margin_days_produces_no_axis_warning_on_every_catalogue_preset[*]`: HALCYON and the starter, with a **modified** view |
| 109.9 | 7 | `test_project_generic_presets.py::test_each_preset_renders_halcyon_and_the_starter[*]`: HALCYON **without** actuals, plus the starter |
| 84.7 / 56.0 | 2 | `test_render.py::test_elevated_preset_reports…` and `…planned_mark_shadow…` (the latter with a **modified** theme) |
| 111.6 | 6 | `test_attached_milestones.py` (two tests of 52 and 56 s) |
| 86.5 | 29 | `test_closure_inputs_are_read.py[*]` (one context, `gallery-editorial-lanes`, is 52 s) |
| 53.4 | 1 | `test_declared_examples_reproduce_by_public_cli` (all contexts, in-process) |
| 28.2 / 25.5 / 24.7 | 3 | `test_issue_466_c3_fallback` (crowded HALCYON), `test_cli_row_height…`, `test_print_mono_separates…` |

Only 36 tests take 5 s or more; they hold 1423 of the 1745 worker-seconds (82%). The other 1822 tests together take about 320 s. So the work is entirely in a few HALCYON renders.

**C. Why a render is expensive** (cProfile of one CLI render, local, relative shares only). The default draft of HALCYON costs about 3 s. The same project through `--preset elevated-light` spent about 98% of its time in `presentation/layout/routing.py::route_orthogonal` (665,000 `clear()` calls into `obstacles.py::collisions`, an all-obstacle scan per candidate segment). Preset renders are 10x to 40x a default render. This is a product performance issue, **not** in scope here (see the review, finding 8); it is why render *count* dominates test time.

## Findings that shape the design

1. `.test_durations` alone should remove most of the imbalance: the three shard sums are 768 / 633 / 343 worker-seconds today; a duration-aware split gives about 581 each.
2. The duplicated HALCYON-with-actuals x preset render is done by the monolith (8 renders), `test_axis_cells` (8) and, for elevated-light, nowhere else in the CLI form. `test_project_generic_presets` renders HALCYON **without** actuals, so it is a different combination and is not a cache hit. `test_cli` margin renders a **modified** view, `test_render` uses in-process `render_review` with other resource combinations. The issue's "3 to 4 files" is therefore 2 files sharing one combination plus 3 files that render their own input. The cache removes about 300 worker-seconds, not most of the 1745.
3. To reach the acceptance figure the remaining big costs must also leave the PR path or shrink: the modified-input margin sweep (343 s) becomes a synthetic PR-path test plus a `corpus` HALCYON sweep, and the whole-corpus sweep `test_declared_examples_reproduce_by_public_cli` (53 s) is already covered on every code PR by the `reproduction-newest-python` job.
4. xdist workers are separate processes and each shard is a separate session on a separate machine. A "session-scoped" cache therefore needs a cross-worker store on disk to honour "at most once per session" under `-n 4`, and it cannot deduplicate across the three shards (see review, finding 2).
5. The estimate after all slices: 1745 - 300 (cache) - 343 + about 30 (margin sweep to synthetic) - 53 (declared examples) = about 1080 worker-seconds, or 90 s per worker across 12 workers, so about 130 to 160 s for the slowest shard with imperfect balance and about 25 s of collection. Acceptance row 1 is **borderline**; it is reported honestly against measurements after each slice, not assumed.

## Open decisions (each resolved in the design)

| # | Decision | Resolved in |
| --- | --- | --- |
| D1 | Cache key, result type and isolation | design section 2 |
| D2 | How workers share one render | design section 2 |
| D3 | What a `corpus` test is, and which tests get it | design section 3 |
| D4 | Where corpus tests run, and how PR shards deselect them | design section 3 |
| D5 | How the durations file is generated and refreshed, and by what token | design section 4 |
| D6 | What is never allowed to leave the PR path | review section "What may not move" |

## Design review questions

1. Does the cache hide a real defect a duplicated render used to catch (determinism, state leakage between renders)?
2. Can a shard still pay for a combination another shard already rendered, and does that break acceptance row 2?
3. Which tests would lose their only PR-path coverage if marked `corpus`?
4. Does a `corpus` mark make a PR able to merge while main fails, and what closes that gap?
5. Is an automated durations refresh possible without weakening branch protection?

## Acceptance evidence to be produced

- Before/after shard times per slice from the slice's own PR CI run, recorded in the PR body and the final report.
- The render-counter test (`tests/support/render_cache.py` plus its guard test) passing on the PR path.
- A table in the I657-3 PR body: each rule that was HALCYON-only, its PR-path synthetic test, and the corpus-marked HALCYON test that remains.
- A full-matrix run (dispatch) on the workflow-change branch showing the `corpus` tests execute and pass.
- The refresh job's first successful run and the resulting `.test_durations` diff.

## Slice order

Design pack (I657-0, this PR) then I657-1 (split and durations), I657-2 (cache), I657-3a (corpus marker and synthetic tests, no workflow change), I657-3b (workflow selection, **awaits the lead**), I657-4 (refresh job and AGENTS.md, workflow, **awaits the lead**). Details are in the [implementation plan](issue-657-pr-pytest-speed-implementation-plan-2026-09-30.md).
