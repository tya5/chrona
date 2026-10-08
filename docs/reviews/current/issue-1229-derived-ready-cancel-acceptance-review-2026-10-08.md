<!-- chrona:literal-acceptance/v1 -->

# Release review — a newer push cancels the older derived-ready run

Implementation: [#1231](https://github.com/tya5/chrona/pull/1231) (merge `bcbb1ab7`). Cause: `derived-ready`, `reproduction-newest-python` and `mcp-floor` were gated by a job-level `if: always()`, which is true for a cancelled run, so `cancel-in-progress` never stopped them. Past run [37708216376](https://github.com/tya5/chrona/actions/runs/37708216376) was superseded at about 00:55Z, yet its `derived-ready` polled 00:54:03 to 01:24:22 (conclusion failure, not cancelled) and held the group. Fix: `!cancelled()` plus a head-SHA check in the wait loop. Plan: [Status comment](https://github.com/tya5/chrona/issues/1229#issuecomment-6056744430).

## Literal issue acceptance

### Issue #1229

- Source: [Issue #1229](https://github.com/tya5/chrona/issues/1229)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On a disposable test PR, pushing twice in quick succession leaves at most one `conformance` / `derived-ready` run active for the newer head, with no manual cancel. | met | Draft PR [#1230](https://github.com/tya5/chrona/pull/1230) (closed, branch deleted): run [37755881535](https://github.com/tya5/chrona/actions/runs/37755881535) had `derived-ready` in progress (polling a check name that never exists); the second push at 09:40:29Z left it `cancelled` at 09:40:54Z, and run [37758292357](https://github.com/tya5/chrona/actions/runs/37758292357) started at 09:40:58Z. | — |
| 2 | The evidence is a pair of run URLs. | met | Before the fix: [37708216376](https://github.com/tya5/chrona/actions/runs/37708216376). After: [37755881535](https://github.com/tya5/chrona/actions/runs/37755881535) and [37758292357](https://github.com/tya5/chrona/actions/runs/37758292357). | — |
| 3 | `derived-ready` semantics are unchanged: it still waits for `derived-main` on the current main tip. | met | [Diff](https://github.com/tya5/chrona/pull/1231/files): only the three `if` lines and a head-SHA check before each poll changed. The #1230 probe kept polling while no `derived-main` run existed; on [#1231](https://github.com/tya5/chrona/pull/1231) `derived-ready` [passed](https://github.com/tya5/chrona/actions/runs/37755895691) against the ready main tip. | — |

## Programme-level criteria (optional)

None.
