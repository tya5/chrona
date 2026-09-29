<!-- chrona:literal-acceptance/v1 -->

# Release Review — #526 acceptance-review gate

## Literal issue acceptance

### Issue #526

- Source: [Issue #526](https://github.com/tya5/chrona/issues/526)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Fix the review structure; main CI is green. | met | [Correction PR #527](https://github.com/tya5/chrona/pull/527) landed as [`24c0d3c5`](https://github.com/tya5/chrona/commit/24c0d3c5ec4e63f06b3130cbea603b438af5f23d); its [exact-main CI run 36500763632](https://github.com/tya5/chrona/actions/runs/36500763632) passed all four jobs, including the literal-review conformance gate. | — |
| 2 | (Process) Close an issue only after the CI run **of the commit that lands its acceptance review** is green, and cite that run. This is already implied by AGENTS.md ("Do not close a ticket while its required release gate … remains unverified"). It is restated here because it slipped. | met | [AGENTS.md rule in correction commit](https://github.com/tya5/chrona/commit/24c0d3c5ec4e63f06b3130cbea603b438af5f23d); [#496 was reclosed](https://github.com/tya5/chrona/issues/496#issuecomment-5881156967) only after [CI 36500763632](https://github.com/tya5/chrona/actions/runs/36500763632) passed on the review-bearing main commit. #526 will likewise remain open until CI on this review-bearing commit passes. | — |

## Programme-level criteria (optional)

None.

## Architecture conclusion

Only contributor procedure and acceptance-review metadata changed. Product contracts, layer ownership, public resources and materializer bytes are unchanged. The corrected #496 review retains its five literal dispositions. No unresolved architectural item remains; close #526 only after the exact main commit carrying this review passes CI.
