<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — Actual history (item 3)

This accepts neither item2 nor the parked item4/#814/#815; the parent stays open.

## Literal issue acceptance

### Issue #902

- Source: [issue902](https://github.com/tya5/chrona/issues/902)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met | Item3 focused evidence only: [fresh-base/state checks, durable replay and immutable revisions](../../../tests/unit/chrona/operational/test_actual_history_engine.py); [real processes](../../../tests/integration/test_actual_history_concurrency.py); [real MCP stdio revert/redo and write gate](../../../tests/mcp/test_mcp_stdio_e2e.py). Item5's separate two-process criterion is reviewed in the work record. | — |

## Programme-level criteria (optional)

Design `a79ab0307`, implementation plan `504478877`, implementation
`c2984c018`, focused review `db9caca1d` and scheduling amendment `f03a8fc86`
are published in that order. The [living work record](../../planning/active/issue-902-store-write-safety-work-record-2026-10-18.md)
contains focused counts and the normative Spec35/10/15/66 consistency review.
Store adapters own persistence, the shared operational engine owns durable
intent/ancestry/CAS validation, and CLI/MCP retain the same gate and dispatch.
Redo revalidates intent; revert creates a new immutable revision. Legacy
unrecoverable intent is diagnosed, not guessed. No renderer or project YAML
changes; generic Project history is unchanged.

Prepared integration `bf83da0e0` includes reviewer1704/1705 and Windows repair
main `381cf404a`; final publication requires its successful trusted-ready gate.
History/process/locking/MCP focused19 and agent/ledger/schema-packaging/CLI115
pass; the literal-review checker passes. Schema equivalence passes: L1 added1/
equal41, L2/L3 with the same five baseline-invalid documents. Independent final
review confirms post-publication record I/O errors propagate rather than being
mislabeled safe rejections. Main-derived changes were merged, not hand-edited.

PR1706's initial CI39102611347 exposed three unclassified identity guards and
schema-migration test expectations. Corrections `d0a2ff526`/`ae21a166c` pass185
focused tests. Independent repair review passes228 address-version, resources,
history, ledger and schema tests: supported v0.3 dispatch remains tested, and
baseline-invalid documents retain their exact declared-version mapping.
Actual-byte identities and canonical request identities are classified
separately. Repaired-main lock/history/process/coverage tests45 and the
history/process/agent batch64 pass. The initial artifact preserves all50
SVG/Scene pairs. Neither
that failed run nor the prepared corrections establish release acceptance.

Release is **not accepted yet**: final current-head PR CI, official artifact
audit and successful exact-main three-OS full release remain required. Item5's
release39101259252 failed Windows; item3 cannot merge until repair PR1707 has
successful native/full release evidence. Under the published scheduling
amendment `146707fc1`, a later successful exact-main run containing BOTH item3
and item2 source changes and literal reviews may accept them together. All
per-item tests and separate PR gates remain mandatory. Parent902 stays open.
