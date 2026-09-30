# Implementation Plan — PR pytest speed and balance (#657)

**Status:** Slices planned; I657-0 (this design pack) is the first publication.
**Design:** [design](../../design/issue-657-pr-pytest-speed-design-2026-09-30.md)
**Review:** [architecture review](../../reviews/current/issue-657-pr-pytest-speed-architecture-review-2026-09-30.md)
**Plan and measurements:** [design plan](issue-657-pr-pytest-speed-design-plan-2026-09-30.md)

Every slice PR: title ends with its slice id, body and commits say `Refs #657` (no closing keyword), the body carries before/after shard times measured from CI (slowest shard, spread), and no assertion is weakened. A slice that edits `.github/workflows/**` opens its PR, gets checks green and stops for the lead to merge.

## Slices

### I657-1 Split the monolith; commit `.test_durations`

- **Files:** `tests/integration/test_readable_defaults.py` (parametrize per id), `.test_durations` (new, repository root).
- **Change:** the loop test becomes `test_default_draft_and_presets_draw_a_distinct_axis_band[default|<preset id>]`; the body is unchanged per id. `.test_durations` is built from the CI per-test measurement in the plan (run 36724348189), mapping the monolith's 201.5 s evenly over its 8 new ids (about 25 s each, matching the per-render cost seen in `test_axis_cells`), in pytest-split's format (`{nodeid: seconds}`, sorted keys). It is generated from CI logs, not a developer machine.
- **Workflow:** none. pytest-split already reads `.test_durations`.
- **Tests:** focused run of the parametrized test (8 ids collected, `default` executed locally); `pytest --collect-only -q` shows the new ids; `pytest --splits 3 --group 1..3 --collect-only` shows all three groups non-empty and their duration sums within 20%, computed with the committed file.
- **Acceptance:** shards on the PR's CI run are balanced; before/after recorded against row 1 (slowest shard, spread).
- **Publication:** own PR, merged by me.

### I657-2 Shared render cache and migration

- **Files:** new `tests/support/render_cache.py`, new `tests/conftest.py` (fixture only), new `tests/integration/test_render_cache.py`, edits to `tests/integration/test_readable_defaults.py` (the split test), `tests/integration/test_axis_cells.py`.
- **Change:** the design's section 2. Migrated tests are exactly those rendering HALCYON with actuals through a copied catalogue preset with unmodified input: the split monolith, `test_print_mono_separates_slips_and_as_of_in_greyscale`, and `test_axis_cells.py` (`test_catalogue_presets_draw_bounded_axis_cells…[*]` and `test_start_aligned_month_labels…`): 17 tests on 8 keys. `test_cli.py`, `test_project_generic_presets.py` and `test_render.py` are inspected and, per the design, are **not** migrated: their renders are modified input, no actuals, or in-process with other resources. The PR body states why for each file. `.test_durations` entries for the migrated tests are left as they are (relative weights only).
- **Tests:** the counter test (`max(render_counts().values()) <= 1`, three call sites of one key give count 1), an isolation test (mutating a returned `scene` and `warnings` does not change the next reader's), a key test (changing an input byte changes the key), a path-rejection test, an explicit determinism test (one combination rendered twice into separate directories, byte-equal). Focused run of the migrated tests with `-n 4` to prove cross-worker sharing.
- **Acceptance:** row 2 through the counter test; before/after shard times in the PR body, and the render log of a local `-n 4` run of the migrated tests (each key once).
- **Publication:** own PR, merged by me.

### I657-3a `corpus` marker and synthetic PR-path tests (no workflow change)

- **Files:** `pyproject.toml` (marker only), `tests/support/axis_projects.py` (or #575's builders if merged), new synthetic tests beside the tests they mirror, and `@pytest.mark.corpus` on the sweeps below.
- **Change:** register the marker; add the synthetic PR-path tests first; then mark. Initial candidates, each subject to the rule table: `test_declared_examples_reproduce_by_public_cli`; the HALCYON leg of `test_cli_margin_days…[*]` (the starter leg stays, and a synthetic project covering the same window across all 7 presets joins it); the `test_closure_inputs_are_read[*]` context sweep and `test_attached_milestones` after audit. Because nothing is deselected yet, the marker merges without changing what any run executes.
- **The rule table** (PR body and this file, updated in place): for every test marked `corpus`, the rule it stood for, whether it was HALCYON-only, the synthetic PR-path test that now guards it, and the mutation check that shows that test failing. No coverage is dropped: a candidate without a synthetic test is not marked and is listed as unmoved.
- **Acceptance:** row 3, first bullet.
- **Publication:** own PR, merged by me. Depends on #575 only for builders if they exist; otherwise independent.

### I657-3b PR shards deselect `corpus` (workflow, awaits the lead)

- **Files:** `.github/workflows/conformance.yml` (add `-m "not corpus"` to the `pr-pytest` command), a guard test `tests/unit/tools/test_ci_corpus_selection.py` parsing the workflow.
- **Change:** one shard-command edit. `reproduction-newest-python` and `full-matrix` are unchanged, so corpus tests run on the schedule, on dispatch and after each push to `main`.
- **Validation:** checks green on the PR; `gh workflow run conformance.yml --ref <branch>` (full matrix) shows the corpus tests executing and passing on all three OSes, linked in the PR body; the PR's shard times show the deselection.
- **Publication:** open, get checks green, **stop and report the PR number to the lead, do not merge.** The lead decides the Python 3.11 reproduction question in the review, "What may not move".

### I657-4 Automated refresh and AGENTS.md (workflow, awaits the lead)

- **Files:** new `.github/workflows/test-durations.yml`, `AGENTS.md` (one paragraph under "Publication and CI discipline").
- **Change:** the design's section 4. The AGENTS.md paragraph gives: what the file is, that the shard command reads it, the weekly job and its manual dispatch, the local refresh command (`pytest -n 4 --store-durations --clean-durations`), and that a stale file costs only balance. AGENTS.md is a docs path in `classify_ci_change.py`, but the workflow file is not, so the PR is a code PR.
- **Validation:** checks green; a manual `workflow_dispatch` of the refresh workflow on the branch produces a `.test_durations` diff in a bot PR (or a clear no-op), linked in the PR body.
- **Publication:** open, checks green, **stop, report the number to the lead, do not merge.** The lead also decides the `DURATIONS_PR_TOKEN` question.

## Measurement protocol

After each slice merges (or, for the workflow slices, once their checks are green), read the slice PR's `pr-pytest` shard step times from its CI run (`Run pytest` step, per shard) and record slowest shard, fastest shard and spread beside the baseline (280 to 416 s slowest, 1.3x to 3.7x spread). The final report states which of row 1's two conditions (slowest under about 150 s; shards within about 20%) is met, and if not, which tests remain. A superseded or cancelled run is not cited.

## Acceptance map

| Row | Slice | Evidence |
| --- | --- | --- |
| 1 | I657-1, -2, -3a/3b (measured after each) | shard step times in each PR body and the final report |
| 2 | I657-2 | `test_each_render_key_renders_at_most_once` and its cross-worker run |
| 3 | I657-3a (table), I657-3b (selection, guard, full-matrix run) | rule table; dispatched full-matrix run |
| 4 | I657-1 (file), I657-4 (job, AGENTS.md) | committed file; refresh run; AGENTS.md paragraph |

The acceptance review is written by the lead after these slices, not here.
