<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — authoring MCP (item 2)

Design `cdf0289f8`, plan `fa31cc79c`, code `fa831e384` and focused review
`0b79e65a0` precede prepared integration `5c363da7d`. Current authority is the
[living work record](../../planning/active/issue-902-store-write-safety-work-record-2026-10-18.md)
and Specs15/35/66. Preparation owns validated candidates; the operational port
owns locking, durable replay, receipt recovery and publication. CLI/MCP share
that path and exact result; the engine does not interpret authoring operations.
Independent review covered containment, crash/retry cleanup, canonical scope,
receipt verification and the gate before reads. No renderer policy changes.

## Literal issue acceptance

### Issue #902

- Source: [Issue #902](https://github.com/tya5/chrona/issues/902)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `apply_authoring_command` as an MCP tool over the guided authoring workspace (`authoring-command-apply` and `workspace revision` exist on the CLI only), with the same write gate and honest annotations. | met | [Tool gate/annotations/exact CLI result](../../../tests/unit/chrona/app/test_agent_authoring.py) and [real MCP stdio](../../../tests/mcp/test_authoring_stdio.py). MCP toolsetv0.6 adds the tool without a separate writer path. Exact-main release39119120797 passed all required release gates below. | — |
| 2 | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met | Item2 [authoring transaction](../../../tests/unit/chrona/operational/test_authoring_commands.py), [durable receipt/recovery](../../../tests/unit/chrona/operational/test_authoring_recovery_receipts.py), [spawned writers](../../../tests/integration/test_authoring_command_transaction.py) and [stdio stale/replay/no-overwrite](../../../tests/mcp/test_authoring_stdio.py). Items3/5 are accepted separately in their reviews. | — |

## Programme-level criteria (optional)

**Item2 release accepted.** PR1708 merged as `0bd24fd4a`; the reviewed
Windows-only test portability repair was included in PR1712. This repair changed
no product code, golden, native lock test or gate; it checks preserved LF/CRLF
bytes and normalizes only the known scratch prefix in OS-error filenames, while
retaining nested filename identity and external absolute paths. Independent
review confirms strict workspace identity is unchanged.

Review-containing exact main `96bdfbb7c` passed
[release39119120797](https://github.com/tya5/chrona/actions/runs/39119120797):
Linux pytest/conformance/probe/wheel/smoke (13,563), macOS (13,568) and Windows
(13,560), plus MCP and newest-Python public reproduction. The full
CLI-characterization module and focused operational/recovery/spawned-writer/
agent/MCP-stdio batch passed199 locally, including missing-workspace, both
newline forms, nested Windows short/long/device paths and an external-path
negative. Items5/3 are accepted in their own reviews. Parent #902 remains open
for owner-parked items4/#814/#815.
