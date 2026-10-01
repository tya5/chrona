# Implementation Plan — PR pytest shard balance (#721 item 1)

**Status:** I721-1a (design pack, #736) and I721-1b (durations refresh, #737) are merged; I721-1c/1d measured and recorded below. No workflow edit was needed.
**Design:** [shard balance design](../../design/issue-721-shard-balance-design-2026-10-01.md) (diagnosis, decisions D1 to D3, acceptance).
**Scope:** item 1 of #721 only. Item 2 (routing) has its own record; item 3 (the refresh job's pull request) is the owner's.

Every slice PR: title ends with its slice id, body and commits say `Refs #721` (no closing keyword), and no assertion is weakened. A slice that edits `.github/workflows/**` opens its PR, gets checks green and stops for the lead to merge. None is planned: the design keeps the shard command.

## Literal acceptance (from the issue, item 1, and the design)

1. The imbalance is diagnosed with data, and a decision on whether a balance target is worth more than the current speed is recorded. (design section 1 and 2)
2. Over at least 8 new PR CI runs: slowest shard at most 100 s in at least 7 of 8 and never above the pre-change slowest; spread at most 20% in at least 6 of 8 (expected not met); honest spread target of at most 25 s in at least 6 of 8. (design section 3)

## Slices

### I721-1a Design and plan (docs)

- **Files:** this plan and the design. Nothing derived.
- **Publication:** docs PR, merged by me.

### I721-1b Refresh `.test_durations` on a post-#735 base (data only)

- **Files:** `.test_durations`.
- **Change:** the file produced by `test-durations.yml` (run `36811762279`, 2837 ids, measured on `32a8c5b0` with `pytest -n 4 --store-durations --clean-durations` on an Ubuntu runner), committed as is. The weekly job would produce the same kind of change; this one lands now because #735 made the recorded weights of the HALCYON items four times too large.
- **Check:** `pytest --collect-only -q --splits 3 --group N -m "not corpus"` shows three groups of equal predicted sum (about 400 worker-seconds, computed from the committed file), no id missing from the file for the tests collected on the base.
- **Publication:** data-only PR, merged by me.

### I721-1c Measure after (no merge)

- **Method:** the next at least 8 PR runs on a base at or after I721-1b. Real PRs are counted as they appear; small throwaway PRs (a one-line comment in a test file, labelled "throwaway, do not merge", closed unmerged) top the count up to 8. Each sample is the `Run pytest` step of the three shards from the jobs API (a cancelled or failed run is not counted), with the fastest, slowest and spread in seconds and percent.
- **Publication:** the table goes into the final report and, as slice evidence, into this record (I721-1d, docs PR).

### I721-1d Record the measured result (docs)

- **Files:** this plan (a results table under "Measured after") and the design (the verdict against the acceptance rows).
- **Publication:** docs PR, merged by me. The acceptance review is the lead's.

## Not planned (and why)

`--dist load`, `--maxschedchunk 1`, longest-first ordering, more or fewer shards, a cross-job queue and splitting the 26 s items were measured or costed in the design and rejected for this slice set. They are reopened only if the pytest step grows past about 150 s again.

## Measured after

Base `6ac9f573` (I721-1b merged: refreshed `.test_durations` on top of the #735 routing speed-up). Eight throwaway PRs (#738 to #745, one comment line in a test file, closed unmerged) opened together, so the 24 shard jobs ran concurrently; the `Run pytest` step per shard, from the jobs API. The run of the I721-1b PR itself (`36813552055`, with the refreshed file in its head) is shown for reference and not counted.

| Sample | Run | Shards 1 / 2 / 3 (s) | Slowest (s) | Spread (s) | Spread (%) |
| --- | --- | --- | --- | --- | --- |
| #738 | `36813908715` | 75 / 72 / 71 | 75 | 4 | 5 |
| #739 | `36813913267` | 74 / 59 / 72 | 74 | 15 | 20 (20.3) |
| #740 | `36813917020` | 73 / 74 / 75 | 75 | 2 | 3 |
| #741 | `36813919529` | 41 / 75 / 72 | 75 | 34 | 45 |
| #742 | `36813922804` | 75 / 74 / 72 | 75 | 3 | 4 |
| #743 | `36813926581` | 36 / 58 / 40 | 58 | 22 | 38 |
| #744 | `36813929409` | 76 / 62 / 73 | 76 | 14 | 18 |
| #745 | `36813932545` | 77 / 50 / 35 | 77 | 42 | 55 |
| (reference) I721-1b PR | `36813552055` | 53 / 74 / 70 | 74 | 21 | 28 |

Before (26 runs, bases `36754302382` to `36804416348`): slowest 112 to 164 s (median 140 s), spread median 37%, 4 of 26 within 20%.

| Acceptance row | Threshold | Result |
| --- | --- | --- |
| Slowest shard | at most 100 s in at least 7 of 8; never above the old slowest | **met**: 8 of 8, maximum 77 s, median 75 s (old median 140 s) |
| Spread, issue target | at most 20% in at least 6 of 8 | **not met**: 4 of 8 (5, 3, 4 and 18%; sample #739 is 20.3%) |
| Spread, honest target | at most 25 s in at least 6 of 8 | **met at the threshold**: 6 of 8 (the two misses are 34 s and 42 s) |

The pattern is two classes of runner (inferred from the earlier probe runs; these samples did not record the CPU). A shard on a slow CPU takes 72 to 77 s; one on a fast CPU takes 35 to 50 s. Runs whose three shards fall in one class are within 5% (#738, #740, #742); runs that mix classes are 38 to 55% apart (#741, #743, #745). The speed half holds with a wide margin; the 20% half is the runner pool, not the split.
