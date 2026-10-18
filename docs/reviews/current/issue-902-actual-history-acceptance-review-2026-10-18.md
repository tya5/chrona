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

Final integration uses trusted-ready main `6d68834de` (reviewer1704 included).
History/process/locking/MCP focused19 and agent/ledger/schema-packaging/CLI115
pass; the literal-review checker passes. Schema equivalence passes: L1 added1/
equal41, L2/L3 with the same five baseline-invalid documents. Independent final
review confirms post-publication record I/O errors propagate rather than being
mislabeled safe rejections. Main-derived changes were merged, not hand-edited.

Release is **not accepted yet**: current-head PR CI, official materializer
artifact audit and full exact-main three-OS pytest/conformance/wheel release
remain required. The item3 merge additionally waits for item5's exact-main
release39101259252 to succeed. No issue closure is authorized by this review.
