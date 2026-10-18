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
| 1 | `apply_authoring_command` as an MCP tool over the guided authoring workspace (`authoring-command-apply` and `workspace revision` exist on the CLI only), with the same write gate and honest annotations. | met | [Tool gate/annotations/exact CLI result](../../../tests/unit/chrona/app/test_agent_authoring.py) and [real MCP stdio](../../../tests/mcp/test_authoring_stdio.py). MCP toolsetv0.6 adds the tool without a separate writer path. Focused evidence only; release pending below. | — |
| 2 | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met | Item2 [authoring transaction](../../../tests/unit/chrona/operational/test_authoring_commands.py), [durable receipt/recovery](../../../tests/unit/chrona/operational/test_authoring_recovery_receipts.py), [spawned writers](../../../tests/integration/test_authoring_command_transaction.py) and [stdio stale/replay/no-overwrite](../../../tests/mcp/test_authoring_stdio.py). This does not accept other items. | — |

## Programme-level criteria (optional)

**Release not accepted.** [PR1708](https://github.com/tya5/chrona/pull/1708)
merged as `0bd24fd4a` after final-head CI39109600057 succeeded. Official
artifact12130285877 preserved all50 SVG/Scene pairs; only two fully classified
diagnostic inventories changed. Earlier diagnostic, CLI-reference, import-set
and skill-length failures were repaired without changing runtime permissions.

[Native full release39110885313](https://github.com/tya5/chrona/actions/runs/39110885313)
passed Linux/macOS but failed two Windows test expectations; Windows wheel was
skipped. The recovery assertion incorrectly reconstructed LF instead of checking
preserved original CRLF bytes. The CLI normalizer missed the absolute filename
from Windows strict path resolution. Under
[the reviewed repair plan](https://github.com/tya5/chrona/issues/902#issuecomment-6247905669),
the tests exercise exact LF/CRLF preservation and normalize only the known
scratch prefix in OS-error filenames, retaining nested filename identity and
external absolute paths. No product code, golden, native lock test or gate
changes. [The publication amendment](https://github.com/tya5/chrona/issues/902#issuecomment-6247917297)
batches this test-only repair into PR1712 before fresh candidate checks and the
mandatory exact-main three-OS full release; the failed run is not acceptance.
Independent review confirms strict workspace identity is unchanged. The full
CLI-characterization module and focused operational/recovery/spawned-writer/
agent/MCP-stdio batch passes199 locally; this includes the exact missing-workspace
case, both newline forms, nested Windows short/long/device paths and an external
path negative. Literal-review and diff checks pass. Native Windows execution
and its wheel gate remain required in the next full release.

Items5/3 are independently accepted on native releases39105269292 and39108421823.
Item2 still requires current-head PR/artifact review and a successful native
full release containing these repairs and this literal review. Parked4/#814/#815
keep parent902 open.
