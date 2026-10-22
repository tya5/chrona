<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1928 rows 1 and 2

Observed on `main` at `e3ec09e9f` (the derived-sync bot commit after [PR #1933](https://github.com/tya5/chrona/pull/1933)). [Issue #1928](https://github.com/tya5/chrona/issues/1928) is the follow-up of the `narrowed` row 5 of [#1832](https://github.com/tya5/chrona/issues/1832) (see [issue-1832-acceptance-review-2026-10-22.md](issue-1832-acceptance-review-2026-10-22.md)). It has two bullets under `Acceptance:` and no comment from anyone else; the body and its comments were re-fetched with `gh issue view 1928 -R tya5/chrona --json body,comments` on 2026-10-23 and counted literally: two rows. The only comment is dev B's own status (written after the first fetch of this review) that cites the run of row 2. Landed: [PR #1931](https://github.com/tya5/chrona/pull/1931) (`e89b25d8d`), which splits the `derived-preview` step of [`conformance.yml`](../../../.github/workflows/conformance.yml) into "Reject derived edits (source-only, timed as its own step)" and "Materialize one PR snapshot". Both rows are `met`.

## Method

The workflow file on `main` was read (lines 84 to 92) and the change of the PR was read with `git show e89b25d8d` (one file, `conformance.yml`, 6 insertions and 4 deletions; `tools/derived_workflow.py` and every test are untouched). The step times of the cited run were read with `gh run view 39856595689 -R tya5/chrona --json jobs,headSha,event,conclusion` on 2026-10-23; the output and the workflow diff are in [ci-step-times-1928.txt](assets-1928/ci-step-times-1928.txt).

## Literal issue acceptance

### Issue #1928

- Source: [Issue #1928](https://github.com/tya5/chrona/issues/1928)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | the time of `source-only` alone is visible per CI run (a separate step, or one elapsed-time line printed by the step), without changing which paths are rejected; | met | `source-only` is now its own step, so every run of `derived-preview` shows its start and end ([`conformance.yml`](../../../.github/workflows/conformance.yml), step "Reject derived edits (source-only, timed as its own step)", lines 84 to 88; the snapshot command is the separate step at lines 89 to 92). In [run 39856595689](https://github.com/tya5/chrona/actions/runs/39856595689) the step ran 21:22:09Z to 21:22:13Z (4 s) and the snapshot step 21:22:13Z to 21:25:25Z (3 m 12 s) ([log](assets-1928/ci-step-times-1928.txt)). Which paths are rejected is unchanged: the diff touches only the workflow file, the two commands, their `env` and their arguments are the same as before, and `tools/derived_workflow.py` is not in the change ([diff in the log](assets-1928/ci-step-times-1928.txt)). | — |
| 2 | one run after the change is cited here with its Actions link. | met | The run is cited on the issue itself, in [dev B's comment](https://github.com/tya5/chrona/issues/1928#issuecomment-6352159344): [run 39856595689](https://github.com/tya5/chrona/actions/runs/39856595689), a `pull_request` run of PR #1931 at head `3db25ee79`, conclusion success, `source-only` 4 s and snapshot 3 m 12 s, as in row 1. The comment was posted on 2026-10-23 while writing this review, because the PR body still reads `RUN_PLACEHOLDER` in its "Cited run" section and the issue had no comment before. | — |

Counts: 2 rows, 2 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document and a log under [assets-1928](assets-1928/ci-step-times-1928.txt); it changes no code, schema, specification, guide, preset, design, example or workflow. The reviewed PR is a CI step layout change only.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
| Reviewed PR #1931 | 0 | 0 | none (workflow triggers, permissions and SHAs unchanged) |
