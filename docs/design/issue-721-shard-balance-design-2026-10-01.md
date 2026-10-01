# Design — PR pytest shard balance (#721 item 1)

**Plan:** [implementation plan](../planning/active/issue-721-shard-balance-implementation-plan-2026-10-01.md).
**Background:** [#657 design](issue-657-pr-pytest-speed-design-2026-09-30.md), [#657 acceptance review](../reviews/current/issue-657-pr-pytest-speed-acceptance-review-2026-10-01.md).

This design changes no product behaviour, schema or public artifact. It decides what, if anything, to change in how the `pr-pytest` shards are split, after measuring where the imbalance comes from. Times below are `Run pytest` step or in-log pytest times from GitHub-hosted runs, never a developer machine.

## 1. What was measured

**Before this work** (26 successful PR runs on bases from `36754302382` to `36804416348`, three shards each, step times): slowest shard 112 to 164 s (median 140 s); fastest-to-slowest spread median 37%; 4 of 26 runs within 20%.

**Instrumented runs.** A throwaway PR (#733, closed unmerged) ran each shard several times in one job on one runner, so that the variants share a CPU, with `-v --durations=0` (per-item completion by worker) and a fixed CPU probe (a 20M-iteration Python loop, `PROBE_SECONDS`, plus `lscpu`). Three rounds:

- Rounds 1 and 2 (runs `36809167917`, `36810123039`, `36811027549`; base `44804ebd`, before the routing speed-up of #735; `.test_durations` as refreshed on 2026-09-30): 18 samples of the production command.
- Round 3 (run `36812223373`; base `32a8c5b0`, after #735), with a `.test_durations` re-measured on that base by the existing refresh workflow (run `36811762279`, 2837 ids).

### Hypotheses against the numbers

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| (a) runner speed varies 1.3 to 2x | **Dominant for the spread between shards.** | The probe ranged 0.93 s to 2.25 s on `ubuntu-latest` (AMD EPYC 9V45 fastest; 9V74, 7763 and Xeon 8573C/8370C slower; the same family varied between 1.5 and 2.2 s on different draws). The same shard (same items, same split) took 59 and 60 s on a 9V45 and 121, 121 and 121 s on a 7763 (shard 2, before #735), and 45 s on a Xeon 8573C against 68 s on a 7763 (shard 1, after #735). Dividing each shard's time by its probe gives 59 to 75 over the 18 samples (mean 68), within 12% of the mean; the raw spread comes from the draw. |
| (b) recorded durations do not predict per-shard work | Rejected for the split, partly true for the weights. | `least_duration` predicted equal sums (402, 404, 404 worker-seconds; 270 of 942 ids per shard had no entry and got the average, a harmless 28%). Probe-normalised shard times agree within 12% of the mean (above). The file was stale after #735 (it still recorded the render items at 34 to 38 s; they now take 9 to 15 s), so the refreshed file differs in placement; see row (d). |
| (c) `--dist worksteal` leaves a long item to start late | **True before #735; the main within-shard loss.** | Before #735, in the 12 samples of shards 1 and 3 the slowest worker ended 17 to 47% (median 36%) after the fastest (for example 142 s total, fastest worker 86 s); shard 2 ended within 0 to 6%. The last 10% of the items took 50 to 100 s on the long-tail shards: items of 20 to 56 s started 40 to 90 s into the run, and a worker that is already running an item cannot give it away (worksteal moves only items a worker has not started). After #735 the items are 6 to 26 s and the loss is 1 to 20% (median 5%) of a 45 to 73 s shard. |
| (d) a few long single items set a floor | **True before #735; mostly gone.** | Before #735 the file recorded eight PR-path preset-render items of 32 to 38 s each and several of 20 to 22 s (the CI runs showed 20 to 56 s, depending on the CPU); the shard times 112 to 164 s were roughly the sum of the shard's items over 4 workers plus a 30 to 56 s tail. After #735 (run `36812223373`): the longest PR-path item is 26 s (`test_schema_equivalence.py::test_gate_passes_on_the_committed_tree`), under half of a 55 to 73 s shard. |
| (e) `least_duration` leaves a coarse remainder | Rejected. | Predicted sums per shard differ by under 1% (402, 404, 404). |

So: **before #735**, the large raw numbers were (d) plus (c) (items of 30 to 40 s, serialised on one worker), on top of (a); **after #735**, the floor and the tail are small, and what remains is (a). Per-test variants of the scheduler were measured on the same runner:

| Variant (same job, same CPU) | Result |
| --- | --- |
| production: `--dist worksteal`, stale durations | shard times 45 to 73 s after #735; worker idle 1 to 20% |
| `--dist worksteal`, durations refreshed after #735 | 45 to 68 s; 0 to 7 s shorter than stale in 6 of 6 pairs (mean -2.7 s, -4%); idle 5 to 21% |
| `--dist load --maxschedchunk 1` (one item at a time), refreshed durations | 52 to 79 s: **slower** than worksteal in 5 of 6 shards (probably because it scatters a module's tests over workers, repeating module-scope setup); idle 3 to 16% |
| the same, items ordered longest first (`--longest-first` hook) | 50 to 92 s: faster only on shard 2 (idle 1%), **35% slower** on shard 1 |
| longest first with `--dist worksteal` (before #735) | no gain: the longest items still queue on the first worker (97 s total with the fastest worker at 66 s) |
| longest first with plain `--dist load` (before #735) | 112 to 237 s: much worse; xdist hands whole chunks in order, so one worker gets all the long items |

## 2. Decisions

**D1. Refresh `.test_durations` on a post-#735 base (data only).** The recorded file describes a tree whose longest items were four times slower. The refresh workflow measured a synced `main` commit (`32a8c5b0`) at 294 s for 2807 tests; it changes no source, and by the measurements above it shortens the shard by a few percent and corrects the weights for 770 ids that had none. This is the one change worth making.

**D2. Keep `--dist worksteal`, `--splitting-algorithm least_duration` and three shards.** None of the scheduler variants measured beats the production command on both the slowest shard and the spread; the two that look good on one shard lose heavily on another. No `.github/workflows/**` edit and no `tests/conftest.py` ordering hook is needed, so nothing in this design affects every contributor's CI.

**D3. Do not chase the raw spread further.** After D1 the spread between the three shards of one run is set by which CPUs the three jobs draw (probe 0.93 s to 2.25 s). Two fixes would remove that, and both are rejected here:

- *More or fewer shards.* The percentage spread comes from the CPU draw, not from the shard size; more shards shorten the step but add a runner (about 25 s of checkout, install and snapshot apply each) and widen the slowest-of-N draw; fewer shards lengthen it. The pytest step is now 45 to 73 s, shorter than `derived-preview` alone (about 100 s).
- *A dynamic queue across the three jobs* (each job claims chunks, for example by creating git refs). It would balance exactly, but it needs `contents: write` on a PR token that is read-only today, a custom plugin, and a failure mode on fork PRs. Not worth it at this step size; revisit only if the pytest step grows back past about 150 s.
- *Splitting the 26 s items* (`test_schema_equivalence.py`): at most a few seconds on the tail of one shard; deferred.

An owner-level alternative, outside the repository: a larger or pinned hosted runner class. Hosted `ubuntu-latest` is a mixed pool.

## 3. Acceptance (stated before the change, not tuned after)

Measured over **at least 8 new PR CI runs** after the refresh merges, each with all three `pr-pytest` shard step times (a cancelled or failed run is not counted; a throwaway PR with a code change gives a sample and is closed):

| Criterion | Threshold | Expectation from the evidence |
| --- | --- | --- |
| Slowest shard, absolute | at most 100 s in at least 7 of 8 runs, and not above the pre-change slowest (112 to 164 s, median 140 s) in any run | holds (45 to 83 s measured after #735) |
| Fastest-to-slowest spread, issue target | at most 20% in at least 6 of 8 runs | **not expected to hold**: it needs the three runners to draw the same CPU class; 4 of 26 prior runs and 1 of 3 post-#735 comparisons met it |
| Spread, honest target | at most 25 s between the fastest and slowest shard in at least 6 of 8 runs, reported next to the percentage | to be measured; at shard times of 45 to 70 s a 20% band is 9 to 14 s, below the runner variance of identical work (59 s against 121 s for one shard before #735, 45 s against 68 s after) |

The acceptance review states which of these held. If the 20% target is not met, the issue records that it is not reachable by splitting alone while the runner pool varies as measured, and that the speed half (slowest shard under 150 s, by a wide margin) holds.

## 4. Result

Measured after the refresh merged (table in the [plan](../planning/active/issue-721-shard-balance-implementation-plan-2026-10-01.md), "Measured after"): slowest shard at most 77 s in 8 of 8 samples (median 75 s, against a median of 140 s before); spread at most 20% in 4 of 8 (the target was 6 of 8, **not met**); spread at most 25 s in 6 of 8 (the honest target, met at the threshold). Of the shard-time reduction, the routing speed-up of #735 accounts for nearly all (140 s to about 60 to 75 s); the refresh adds about 4%. The remaining spread is the runner-CPU draw (slow-class shards 72 to 77 s, fast-class 35 to 50 s for the same split, inferred from the earlier probe runs); the three samples with a fast-class shard are the three with spreads of 38% or more. The 20% target is not reachable by changing the split while the hosted pool varies as measured; the samples ran concurrently (24 jobs at once), which may exaggerate the pool mix.
