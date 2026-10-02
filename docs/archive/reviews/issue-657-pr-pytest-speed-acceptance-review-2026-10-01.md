<!-- chrona:literal-acceptance/v1 -->

# Issue #657 — PR pytest speed acceptance review

Source: [Issue #657](https://github.com/tya5/chrona/issues/657), observed 2026-10-01 (body last edited 2026-09-30; no comments). Design pack, published in [PR #666](https://github.com/tya5/chrona/pull/666): [design plan](../planning/issue-657-pr-pytest-speed-design-plan-2026-09-30.md), [design](../../design/issue-657-pr-pytest-speed-design-2026-09-30.md), [architecture review](issue-657-pr-pytest-speed-architecture-review-2026-09-30.md) and [implementation plan](../planning/issue-657-pr-pytest-speed-implementation-plan-2026-09-30.md).

Slices, each merged with its PR CI green (PR #698 carries only the refreshed data file and was opened by hand):

| Slice | PR | Merge | PR CI |
| --- | --- | --- | --- |
| I657-0 design pack (plan, design, review, implementation plan) | [#666](https://github.com/tya5/chrona/pull/666) | [`3eca6f78`](https://github.com/tya5/chrona/commit/3eca6f78a2b34e71713d54da0ecc82154092df29) | [run](https://github.com/tya5/chrona/actions/runs/36728760887) |
| I657-1 split the axis-band loop test per preset, commit `.test_durations` | [#667](https://github.com/tya5/chrona/pull/667) | [`abdcbc29`](https://github.com/tya5/chrona/commit/abdcbc298c534b96d820a45e2519c448cf2534f2) | [run](https://github.com/tya5/chrona/actions/runs/36730684398) |
| I657-2 session render cache with a render counter | [#670](https://github.com/tya5/chrona/pull/670) | [`f9eaa051`](https://github.com/tya5/chrona/commit/f9eaa051600e3be448e088241b06c25d499bad1f) | [run](https://github.com/tya5/chrona/actions/runs/36733307922) |
| I657-3a `corpus` marker and synthetic PR-path twins | [#671](https://github.com/tya5/chrona/pull/671) | [`94053855`](https://github.com/tya5/chrona/commit/94053855e8b75a01f51c6df48fb677d1386ff3f6) | [run](https://github.com/tya5/chrona/actions/runs/36735832378) |
| I657-2b one test item per HALCYON preset render | [#677](https://github.com/tya5/chrona/pull/677) | [`29fd7390`](https://github.com/tya5/chrona/commit/29fd7390d92d77e3c22943f5657837346a502393) | [run](https://github.com/tya5/chrona/actions/runs/36745493158) |
| I657-3b PR shards deselect `corpus`, `--dist worksteal`, refreshed durations | [#683](https://github.com/tya5/chrona/pull/683) | [`05610607`](https://github.com/tya5/chrona/commit/056106074b6d26f20c05ec89253a4c5c0d20ec39) | [run](https://github.com/tya5/chrona/actions/runs/36748538167) |
| I657-4 weekly durations refresh workflow and AGENTS.md text | [#685](https://github.com/tya5/chrona/pull/685) | [`712c2945`](https://github.com/tya5/chrona/commit/712c2945008243342d3349c0c2ee6906b762f909) | [run](https://github.com/tya5/chrona/actions/runs/36749350300) |
| I657-4 refresh measures a synced main commit | [#690](https://github.com/tya5/chrona/pull/690) | [`5344b505`](https://github.com/tya5/chrona/commit/5344b5050be9e7254a5e74010afd2e924b7fd03a) | [run](https://github.com/tya5/chrona/actions/runs/36754302382) |
| I657-4 first refreshed `.test_durations` (PR opened by hand) | [#698](https://github.com/tya5/chrona/pull/698) | [`7f20b912`](https://github.com/tya5/chrona/commit/7f20b9124aa4daf7e7ddc46100c118590a0ebbea) | — |
| I657-4 warn instead of failing when the refresh PR is refused | [#700](https://github.com/tya5/chrona/pull/700) | [`913c962e`](https://github.com/tya5/chrona/commit/913c962eda74a8748446d1500188d7375c7b829f) | [run](https://github.com/tya5/chrona/actions/runs/36768908273) |

## Literal issue acceptance

### Issue #657

- Source: [Issue #657](https://github.com/tya5/chrona/issues/657)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | PR-path pytest wall-clock time (the slowest shard) is under about 150 s on a code PR, and the shards are within about 20% of each other. | narrowed | The speed half holds. The issue measured the shards at 421, 260 and 170 s on [PR #654](https://github.com/tya5/chrona/pull/654). On the pytest step of 12 successful PR runs after the refreshed durations landed (#698, 2026-09-30) the slowest shard was 112 to 152 s (median about 137 s; one run at 152 s, the rest at 149 s or less). The balance half does not hold: the spread between the fastest and slowest shard was 0 to 53% with a median of about 34%, and only 2 of 12 runs were within 20% (for example `145 / 132 / 89`, `67 / 124 / 144`, `131 / 131 / 130`). One sample straight after the refresh, `125 / 125 / 122`, looked balanced and the series shows it was luck. | [#721](https://github.com/tya5/chrona/issues/721) |
| 2 | Each (project, preset) combination is rendered at most once per test session in the PR path. A test asserts this through the fixture's render counter. | met | The [session render cache](../../../tests/support/render_cache.py) hands the Scene, SVG and diagnostics of one committed input to every test that uses it unmodified, and [`test_render_cache.py`](../../../tests/integration/test_render_cache.py) asserts through its render counter that each key renders once. The cache alone did little because pytest-split places items one by one, so consumers of one preset landed on different shards (six of seven preset keys rendered twice); [PR #677](https://github.com/tya5/chrona/pull/677) moved the four rule checks verbatim into [`preset_checks.py`](../../../tests/support/preset_checks.py) and runs them in one item per render. The counter was checked locally across xdist workers; the per-shard render count could not be read from CI. | — |
| 3 | No test coverage is lost: every rule tested before still has a PR-path test (synthetic where it was HALCYON-only); `corpus`-marked tests run on main, nightly and manual runs; the full suite still passes on those runs. | met | Each `corpus`-marked test has a PR-path twin recorded in [PR #671](https://github.com/tya5/chrona/pull/671): the margin-days check on the starter and a synthetic nine-month project for all seven presets, [`test_visual_treatment_synthetic.py`](../../../tests/integration/test_visual_treatment_synthetic.py) for the elevated and planned-shadow rules (each fails if the baseline profile is flipped), the declared-examples reproduction in `reproduction-newest-python` on every code PR, and 28 of 29 contexts of the closure-inputs test. The PR shards deselect `corpus` only from [PR #683](https://github.com/tya5/chrona/pull/683), checked by [`test_ci_corpus_selection.py`](../../../tests/unit/tools/test_ci_corpus_selection.py). The full matrix has no marker filter and passed on all three OSes with the corpus tests running: [run 36749103514](https://github.com/tya5/chrona/actions/runs/36749103514) on the #683 branch (1974 to 1978 passed) and [run 36794029475](https://github.com/tya5/chrona/actions/runs/36794029475) on `main` (`87f66d44`). | — |
| 4 | `.test_durations` is committed and refreshed by an automated job, and AGENTS.md says how. | narrowed | [`.test_durations`](../../../.test_durations) is committed ([#667](https://github.com/tya5/chrona/pull/667)) and was regenerated on a CI runner ([#683](https://github.com/tya5/chrona/pull/683), [#698](https://github.com/tya5/chrona/pull/698)). [AGENTS.md](../../../AGENTS.md) describes the file, the weekly job, the manual refresh and the `corpus` marker ([#685](https://github.com/tya5/chrona/pull/685)). The job `test-durations.yml` ran end to end on 2026-09-30 ([run 36754892251](https://github.com/tya5/chrona/actions/runs/36754892251): it selects a synced `main` commit, measures 1997 tests in about 400 s and pushes `bot/test-durations`), but it cannot open its own pull request because the repository setting "Allow GitHub Actions to create and approve pull requests" is off. Since [#700](https://github.com/tya5/chrona/pull/700) it warns with the compare URL instead of failing, and the refresh PR is opened by hand (#698 was). The first scheduled Monday run has not happened yet. | [#721](https://github.com/tya5/chrona/issues/721) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Tests and CI only; no product change. The PR path is much faster (the slowest shard fell from 421 s to about 137 s at the median) without dropping a rule from the PR path. The two `narrowed` rows are the balance target and the last step of the automated refresh, both recorded in #721 with their evidence.

Disclosures:

- **A defect in the refresh workflow I merged.** The first run checked out `main`'s raw tip, a pre-sync commit with stale derived evidence, and failed one reproduction test; I missed the race with derived-sync in review. It was fixed in [#690](https://github.com/tya5/chrona/pull/690) (select the newest `main` commit whose `derived-main` check run succeeded) and [#700](https://github.com/tya5/chrona/pull/700).
- **One merge with `derived-ready` red.** [PR #698](https://github.com/tya5/chrona/pull/698) (data only) was merged after every substantive check passed, because `derived-ready` failed only on its stale-base recheck while `main` moved during the run.
- **Python 3.11 on the PR path.** `test_declared_examples_reproduce_by_public_cli` runs on 3.12 for every code PR and on 3.11 only in the full matrix, because it is `corpus`-marked.
- **`--dist worksteal`** was added to the shard command; the original design did not include it. Without it, equal predicted sums gave 166 / 87 / 143 s.
- **The routing hot spot.** About 98% of a HALCYON preset render is `route_orthogonal`; that is a product change, recorded in #721.
- **Owner action.** Enabling the Actions pull-request setting or adding `DURATIONS_PR_TOKEN` completes row 4.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #657; record that run in the issue closing comment.
