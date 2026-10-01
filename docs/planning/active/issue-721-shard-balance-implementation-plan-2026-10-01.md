# Implementation Plan — PR pytest shard balance (#721 item 1)

**Status:** I721-1a (this design pack) is the first publication.
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
