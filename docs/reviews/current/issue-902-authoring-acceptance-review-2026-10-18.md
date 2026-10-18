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

**Release pending.** PR1708 merged at `0bd24fd4abdfb35b40323a3b1a97e445a728d9c4`
on ready main `b12cbd7b49c476013ce339c01dbd66161be9f4f2`; exact-main full
release39110885313 is still in progress. Item2 cannot be marked release-accepted
until that run succeeds. Repair
`8030a353e` follows [plan6247290279](https://github.com/tya5/chrona/issues/902#issuecomment-6247290279);
the combined diagnostics/operational/recovery/agent/transaction/lock/MCP-stdio
batch passes112. Import-direction and literal-review checks pass. Earlier
focused batches overlap and are not additive.

CI39108636652 on199272f90 failed conformance and pytest shards2/3. All failures
are accounted for: four helper calls lacked following diagnostic context; the
CLI reference was stale (also shard2); the exact import-set test omitted the
approved authoring port (shard2); and the skill exceeded its200-line limit
(shard3). Private guards now take `(code, path)` with identical runtime messages
and failure predicates; direct tests retain those owner paths. Diagnostic
validation has no bare/unclassified sites or policy exclusions. The existing
CLI-reference generator refreshed only MCP help copy; grammar is unchanged.
The import expectation now includes only the approved port, with positive and
SDK-binding rejection coverage; production permissions are unchanged. The skill
is200 lines, preserving write authorization, stale-base and durable replay rules.
The exact affected import/CLI/skill batch passes78 tests; skill validation,
import-direction and generated CLI-reference checks pass. No gate was weakened.
Its official artifact12129351876 retains all50 SVG/Scene pairs and changes only
two reviewed diagnostic inventories; that old artifact is not final acceptance.
The merged PR has passed its current-head checks and its publication artifact
was reviewed; the exact-main full release remains the final item2 gate. Item5's
repaired exact-main release39105269292 passed all native gates, and item3 was
accepted independently by exact-main release39108421823. Parked4/#814/#815
keep parent902 open.
