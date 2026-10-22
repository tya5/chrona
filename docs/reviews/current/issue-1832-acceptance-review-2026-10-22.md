<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1832 rows 1 to 5

Observed on `main` at `b1935990b` (the derived-sync bot commit after [PR #1923](https://github.com/tya5/chrona/pull/1923); the later tip only adds a docs PR). [Issue #1832](https://github.com/tya5/chrona/issues/1832) has no numbered rows; its `Acceptance:` paragraph holds three semicolon-separated clauses, and the reviewer's one comment (2026-10-20) adds two requirements. The body and its one comment were re-fetched with `gh issue view 1832 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: three clauses, plus the two requirements of the comment (build once with identical semantics and a test that the per-path result equals the old one; record the before/after time of the source-only step in CI), where the first of the two is one row because it names one test. That is five rows. Landed in [PR #1836](https://github.com/tya5/chrona/pull/1836) (`0f1dbe938`). Rows 1 to 4 are met; row 5 is narrowed to a CI time of the whole step and has the follow-up [#1928](https://github.com/tya5/chrona/issues/1928).

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`. After tree: `b1935990b`. Before tree: `0bf7031c6`, the parent of the #1836 merge, as a detached worktree. Tests: [pytest-1832.txt](assets-1832/pytest-1832.txt) (21 passed, the whole file). Before and after: [before-after-1832.txt](assets-1832/before-after-1832.txt), produced by one script, [probe-1832.py.txt](assets-1832/probe-1832.py.txt), that runs `derived_workflow source-only` end to end through `main()` on a 38-path diff of the real repository (19 declared outputs and 19 source files, `git diff` stubbed), counting `derived_paths(root)` calls and wall time. CI times: [ci-step-times-1832.txt](assets-1832/ci-step-times-1832.txt), read from `gh run view` for the two Actions runs the PR cites.

## Literal issue acceptance

### Issue #1832

- Source: [Issue #1832](https://github.com/tya5/chrona/issues/1832)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | synthetic tests prove one inventory construction for a multi-file diff and identical admission/rejection including retired outputs; | met | `test_source_only_builds_inventory_once_with_unchanged_per_path_results` ([`test_derived_workflow.py`](../../../tests/unit/tools/test_derived_workflow.py), added by PR #1836) stubs `derived_paths`, runs `main()` as `source-only` on a seven-path diff (a declared output, a retired / generated-prefix output, a scene JSON, an authored manifest, a source file, a traversal path and a report), asserts exactly one `derived_paths` call, and asserts the rejected list equals the old per-path computation, so admission and rejection are identical, including the retired output (passes, [log](assets-1832/pytest-1832.txt)). The real-repository run shows the same: 38 paths, 19 rejected before and after, one result hash for both trees ([log](assets-1832/before-after-1832.txt)). Fail-closed behaviour is unchanged: `is_derived_path` still ends in `path in inventory or _is_derived_path(path)` ([`tools/derived_workflow.py`](../../../tools/derived_workflow.py), lines 161 to 169). | — |
| 2 | affected existing derived-workflow tests pass; | met | All 21 tests of `tests/unit/tools/test_derived_workflow.py` pass on `b1935990b`, including the 20 that existed before the PR ([log](assets-1832/pytest-1832.txt)). | — |
| 3 | report before/after profiler/call-count evidence rather than a borrowed runtime threshold. | met | The PR body reports call counts (38 builds to 1) and local wall time (121.8 s to 3.0 s) for the same 38-path check, with no threshold. Reproduced here with one script on the two trees: `derived_paths` builds 38 before and 1 after; wall 111.8 s before (an earlier run of the same tree: 134.9 s) and 3.0 s after; the rejection result is identical ([log](assets-1832/before-after-1832.txt)). The count is the evidence; the wall time varies by about 20 s between runs on this machine. | — |
| 4 | Build the inventory once per invocation with identical semantics, add a test that the per-path result equals the old one (reviewer comment of 2026-10-20). | met | `main()` builds `derived_inventory(root)` once (only when the diff is non-empty) and passes it to `is_derived_path(path, root, inventory)`; without the argument the function still builds it itself, so existing callers keep their semantics (lines 161 to 169 and 324 to 327 of [`tools/derived_workflow.py`](../../../tools/derived_workflow.py)). The test of row 1 compares both the shared-inventory path and the no-argument path with the old per-path expression, element by element (`== old` twice), and asserts the cases are mixed (`any(old) and not all(old)`). | — |
| 5 | and record the before/after time of the source-only step in CI (reviewer comment of 2026-10-20). | narrowed | Recorded, but for the whole step, not for `source-only`. The PR body records the `derived-preview` step "Reject derived edits and materialize one PR snapshot": 211 s before ([run 39437809785](https://github.com/tya5/chrona/actions/runs/39437809785)) and 133 s after ([run 39444878694](https://github.com/tya5/chrona/actions/runs/39444878694)); both figures reproduce from the step timestamps ([log](assets-1832/ci-step-times-1832.txt)). That step runs `source-only` and then `snapshot` in one `run:` block ([`conformance.yml`](../../../.github/workflows/conformance.yml), lines 84 to 90), `source-only` prints nothing on success, and neither log has a timestamp between the two commands, so the time of `source-only` alone is not in the record and cannot be recovered from these runs; the PR says so itself ("not isolated source-only time"). The 78 s drop is consistent with, but does not prove, the local 3.0 s versus 111.8 s measurement of row 3. | [Issue #1928](https://github.com/tya5/chrona/issues/1928) |

Counts: 5 rows, 4 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, logs and a script copy under [assets-1832](assets-1832/pytest-1832.txt); it changes no code, schema, specification, guide, preset, design, example or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
