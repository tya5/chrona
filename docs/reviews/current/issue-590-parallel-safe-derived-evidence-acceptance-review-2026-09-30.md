<!-- chrona:literal-acceptance/v1 -->

# Issue #590 — parallel-safe derived evidence acceptance review

Source: [Issue #590](https://github.com/tya5/chrona/issues/590), observed 2026-09-30. Design, slices, the production proofs and the required/hardening split: [work record](../../planning/active/issue-590-parallel-safe-derived-evidence-work-record-2026-09-29.md).

## Literal issue acceptance

### Issue #590

- Source: [Issue #590](https://github.com/tya5/chrona/issues/590)
- Observed: 2026-09-30

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Two PRs that each change a different Theme role can merge in either order without conflicts in derived files. Demonstrate this with two test PRs. | met | Two source-only Theme changes (Orion `timeline-row-height`, Controller Z `progress-inset`) were opened as four disposable PRs, [#639](https://github.com/tya5/chrona/pull/639) to [#642](https://github.com/tya5/chrona/pull/642), against two bases and merged in opposite orders, A then B and B then A, with no conflict and no derived file in either diff. The two resulting source trees were identical. After `derived-sync` on each base ([36655297576](https://github.com/tya5/chrona/actions/runs/36655297576), [36655307749](https://github.com/tya5/chrona/actions/runs/36655307749)) the regenerated trees were identical too. Recorded in the [work record](../../planning/active/issue-590-parallel-safe-derived-evidence-work-record-2026-09-29.md) (PR [#643](https://github.com/tya5/chrona/pull/643)). | — |
| 2 | A PR whose sources would produce different derived output shows that diff in CI and does not fail for "stale committed evidence". | met | Every PR's `derived-preview` job regenerates one disposable snapshot and uploads a bounded before/after artifact, and the PR check rejects only hand-edited derived paths. All four proof PRs passed conformance, the three pytest shards and the newest-Python reproduction with changed derived output. A PR that hand-edited a derived file failed `derived-preview` and `derived-ready` (PR [#634](https://github.com/tya5/chrona/pull/634), closed unmerged). | — |
| 3 | `main` is never left with stale derived files for longer than one post-merge job. A failing regeneration on main is visible and blocks the next merge. | deferred | Staleness and visibility are met: every push to `main` enters one serialized `derived-sync`, which regenerates, publishes one bot commit or a no-op and dispatches the three-OS run on the final SHA. Production runs: no-op [36639811376](https://github.com/tya5/chrona/actions/runs/36639811376), changed path [36647695242](https://github.com/tya5/chrona/actions/runs/36647695242) (bot commit `a18e0a5a`, exact-main [36647931251](https://github.com/tya5/chrona/actions/runs/36647931251) green), recovery from stale evidence [36644882789](https://github.com/tya5/chrona/actions/runs/36644882789). A failed sync shows as a failed run and leaves `derived-ready` absent on that tip, so a later PR's `derived-ready` fails. **Enforcement is not applied to `main`:** the owner decided on 2026-09-30 that there is no reason to protect it now. The route is proved on a disposable protected branch (bot fast-forward under the rule, and a merge refused with HTTP 405, [work record](../../planning/active/issue-590-parallel-safe-derived-evidence-work-record-2026-09-29.md), PRs [#633](https://github.com/tya5/chrona/pull/633) and [#635](https://github.com/tya5/chrona/pull/635)). | [#645](https://github.com/tya5/chrona/issues/645) holds the enforcement, with the proved route and its own acceptance. |
| 4 | `AGENTS.md` describes the flow. | met | [AGENTS.md](../../../AGENTS.md), "Publication and CI discipline": source-only PRs and the disposable snapshot, the serialized main sync with its immutable candidate and trusted gate, the commit-status route, and the statement that failed syncs are claimed to block merges only once protection is configured. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Only CI and process change: no resource schema, Layout, Scene or adapter change, and Specs 22 and 40 keep byte authority over derived output, now published by the sync instead of by each PR. The trusted-gate machinery stays because it is what lets the bot commit satisfy a required check. The disposable `derived-proof/*` target used for the proofs was removed (PR [#644](https://github.com/tya5/chrona/pull/644)).

Row 3 is **deferred**, so under AGENTS.md this issue stays open until the reviewer and the owner approve the successor disposition (#645) or protection is enabled. The exact-main three-OS run for the commit that publishes this review is cited in the closing comment, after that disposition.
