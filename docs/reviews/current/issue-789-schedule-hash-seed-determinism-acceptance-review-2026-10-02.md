<!-- chrona:literal-acceptance/v1 -->

# Issue #789 — `chrona schedule` byte determinism acceptance review

Source: [Issue #789](https://github.com/tya5/chrona/issues/789), observed 2026-10-02 (body plus one comment, mine, the claim and decision record; last updated 2026-10-02). The issue's acceptance section has one checkbox; the table copies it literally. Work record: [issue-810-789-scheduler-analysis-work-record-2026-10-02.md](../../planning/active/issue-810-789-scheduler-analysis-work-record-2026-10-02.md).

Slices: docs [PR #835](https://github.com/tya5/chrona/pull/835) (`15a7e218`); implementation [PR #837](https://github.com/tya5/chrona/pull/837) (`471e8284`).

## Literal issue acceptance

### Issue #789

- Source: [Issue #789](https://github.com/tya5/chrona/issues/789)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona schedule` (and every other command whose JSON is deterministic by contract) prints identical bytes under at least eight different `PYTHONHASHSEED` values, covered by a test that runs the command in subprocesses with different seeds over the starter and HALCYON-1; the characterization suite no longer needs to sort `totalFloat`. | met | [`test_hash_seed_determinism.py`](../../../tests/cli/test_hash_seed_determinism.py) runs the real CLI in subprocesses under seeds 0 to 7 and requires identical exit code, stdout and stderr for `schedule`, `validate` (starter and HALCYON-1) and `compile` (a derived-gates plan and the HALCYON-1 terse plan); it also pins the Spec 57 order of `totalFloat` and `criticalObjectIds`, and of `latest_placements` and `component_targets` under every seed. The failing-first commit failed for both `schedule` cases. Source fix: `_analyze_criticality` keys `totalFloat` and `latest_placements` in Project object order, the order Spec 57 already stated. `_canonical_schedule` is deleted from [`test_cli_characterization.py`](../../../tests/cli/test_cli_characterization.py), which now records `totalFloat` as printed. Scan of the other commands (four seeds, stdout, stderr and written file hashes): `preset list`, `identity bytes`, `identity document`, `mcp --list-tools` and `render` of the starter and HALCYON-1 are identical; the analysis was the only mapping the CLI builds from a set. MCP `schedule_project` sorts its mappings itself (Spec 66) and its bytes are unchanged. Three mutants (set iteration again, `latest_placements` unordered, sort by id) were each killed. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The scheduler now owns the order of what it emits, so no adapter has to sort a scheduler mapping; Spec 57 gains the sentence that every analysis mapping is keyed in Project object order. No schema, port or import direction changed.

The CLI characterization golden changed in four schedule records (`schedule-starter-ok`, `schedule-halcyon-ok`, `schedule-snapshot-ok`, `schedule-deadline-warning`). Parsed and compared with the previous golden, the content is identical and only `totalFloat` is in Project object order instead of sorted order; the diff was reviewed in PR #837. A sweep of 52 runs (every tracked Project, scenario and compilable terse fixture, whole analysis) is byte-identical under hash seeds 1 and 5.

Disclosures:

- The scan covers the commands that need no Store or snapshot; the Store-bound commands (`review`, `baseline-compare`, `render-review`, `materialize`, `init`) were not scanned and are not part of the seed test. The fix removes the only source found, the scheduler analysis they may consume; a hash-ordered mapping elsewhere in them would be a new finding, not a gap in this fix.
- `schedule` of a plan that previously raised (#810) is a separate change, accepted in its own review.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #789; record that run in the issue closing comment.
