<!-- chrona:literal-acceptance/v1 -->

# Issue #1632 — protected detour acceptance

Implementation landed in [ccf93c0e4 / PR #1644](https://github.com/tya5/chrona/pull/1644).
[Exact-head PR CI](https://github.com/tya5/chrona/actions/runs/39014066410)
passed all three pytest shards, conformance and newest-Python reproduction.

## Literal issue acceptance

### Issue #1632

- Source: [Issue #1632](https://github.com/tya5/chrona/issues/1632)
- Observed: 2026-10-17

[Reviewer clarification](https://github.com/tya5/chrona/issues/1632#issuecomment-6230873879)
requires row 1 under both `relax` and `suppress`.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic 22-task chain grouped by 9 owners renders sunday in a time comparable to the unchained plan. | met | [Synthetic matrix](https://github.com/tya5/chrona/blob/ccf93c0e49e65027ae7872e072bcbf657c61432a/tests/integration/test_sunday_grouped_chain.py): 22 tasks, 9 owners, 3 rollups, both modes, chained and unchained. All 21 relations retained; suppress exercises 9 barrier proofs without through-mark, suppression or false exhaustion. Observed chained/unchained suppress: 2.23/0.78 s wall, 2.03/0.69 s CPU; observations, not an invented threshold. Exact public 5/22-task inputs also finish with all 4/21 routes. | — |
| 2 | Public SVG/Scene changes listed with counts. | met | [Official exact-head snapshot](https://github.com/tya5/chrona/actions/runs/39014066410), artifact `derived-snapshot-c785586d1b9a4d450e65348d3ddd88f9fc769f21`: 50 SVGs and 50 Scenes byte-identical to base. Every slide: 0 routes, labels or primitives added, removed or changed. Only diagnostic inventory source line references change. | — |

Focused groups: 322 routing/ports/history/resolution/Sunday tests, final 22
bound/protected/grouped tests, and 73 completion/entry/wiring tests passed.
[Profile and public inputs](https://github.com/tya5/chrona/issues/1632#issuecomment-6230169070).

## Programme-level criteria (optional)

Released on exact review-containing main `cd4dae681c9fd09f2c26d0dd037fcdac8d97e82d`:
[run39016025968](https://github.com/tya5/chrona/actions/runs/39016025968) passed
three-OS full pytest/conformance/wheel and newest-Python public reproduction.
The reviewer confirmed the actual trial and closed issue1632 with that evidence.

## Architecture conclusion

Spec50 clarification was published before code (35c710d58). The conservative
proof uses final required primary interiors, excludes authorized hosts, combines
bounds by maximum, and requires endpoint-preserving completion. All completed
safety validators and other pairs remain active; no-safe-path cases retain natural
domain exhaustion. No runtime quota, timeout or general polynomial-time claim.
Layout owns geometry/routes; Scene, adapters, Project and schemas are unchanged.
Independent read-only review found no blockers.
