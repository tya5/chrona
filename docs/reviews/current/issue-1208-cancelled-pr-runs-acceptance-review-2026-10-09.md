<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — obsolete PR runs kept alive by `always()` (duplicate of #1229)

#1208 reports that a superseded PR head's `reproduction-newest-python` kept running, leaving the current head pending until a manual force-cancel. Its cause and suggested fix (job-level `always()` replaced by a cancellation-aware condition) are exactly the cause and fix of [#1229](https://github.com/tya5/chrona/issues/1229), delivered by [#1231](https://github.com/tya5/chrona/pull/1231) (`db81ac1b`, merge `bcbb1ab7`) and accepted in [the #1229 review](issue-1229-derived-ready-cancel-acceptance-review-2026-10-08.md). No further change is needed; this review closes #1208 as met, a duplicate of #1229.

Evidence from `main` at `f0fb4018`: [`.github/workflows/conformance.yml`](../../../.github/workflows/conformance.yml) has `if: ${{ !cancelled() && ... }}` on `reproduction-newest-python` (line 142), `mcp-floor` (168) and `derived-ready` (184); the remaining `always()` are step-level artifact and diagnostics steps, which do not keep a cancelled run alive. `derived-ready` also exits with `superseded by <sha>` once the PR head moved.

## Literal issue acceptance

### Issue #1208

- Source: [Issue #1208](https://github.com/tya5/chrona/issues/1208)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Superseding a PR head terminates its obsolete workflow and allows current-head conformance to start without manual force-cancel. | met | The three job-level conditions are `!cancelled()` ([workflow](../../../.github/workflows/conformance.yml)); run [37755881535](https://github.com/tya5/chrona/actions/runs/37755881535) was cancelled 25 s after the second push and [37758292357](https://github.com/tya5/chrona/actions/runs/37758292357) started at once, with no manual cancel (the #1229 evidence pair). | — |
| 2 | Required independent checks still run after sibling failures on the current head and on scheduled/dispatched exact-main release runs. | met | `!cancelled()` is true after a sibling failure, so the independent jobs still start; their conditions keep the `schedule` and `workflow_dispatch` branches ([workflow](../../../.github/workflows/conformance.yml)). Exact-main three-OS run [37763305614](https://github.com/tya5/chrona/actions/runs/37763305614) is green. | — |
| 3 | Final-head and exact-main acceptance evidence remain required; cancelled obsolete-head runs are not counted as successful validation. | met | `derived-ready` still asserts `success` of the preview, conformance, pytest and newest-python results and the exact base tip, so a cancelled sibling (result `cancelled`) fails it; it also fails when the head is superseded ([workflow](../../../.github/workflows/conformance.yml)); no release gate was weakened ([#1229 review](issue-1229-derived-ready-cancel-acceptance-review-2026-10-08.md)). | — |

## Programme-level criteria (optional)

None.
