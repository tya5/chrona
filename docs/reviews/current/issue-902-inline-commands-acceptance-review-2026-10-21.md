<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — inline commands (item 4)

Design and plan: `cfa3e22e3837aa62842a136452b2ff9645e24aba`;
implementation: `bf9ef2d85`. Current authority is the
[work record](../../planning/active/issue-902-store-write-safety-work-record-2026-10-18.md)
and [Spec66 §2.1](../../specification/66-agent-interface.md).
Independent review found no separate parser, request identity, transaction,
write-gate or containment path. Only the tool input boundary changes; Store,
authoring preparation/transactions and rendering owners remain unchanged.

## Literal issue acceptance

### Issue #902

- Source: [reviewer acceptance](https://github.com/tya5/chrona/issues/902#issuecomment-6294800291)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | An MCP stdio test where an agent with no file access validates a plan, applies an inline edit, reverts it and renders, using only tool calls. | met | [MCP-only lifecycle](../../../tests/mcp/test_workspace_lifecycle_stdio.py): no client file operations, inline edit/inverse, returned embedded SVG verified. | — |
| 2 | Inline and path forms produce identical revisions for the same command. | met | [Store parity and integrity](../../../tests/unit/chrona/app/test_agent_commands.py), [Store stdio](../../../tests/mcp/test_inline_store_commands_stdio.py), and [authoring twin-workspace stdio](../../../tests/mcp/test_workspace_lifecycle_stdio.py) compare revisions and mixed-form replay; stale/reused IDs and immutable outputs remain protected. | — |
| 3 | The tool descriptions state both forms, with the exact version literal (as in #1807). | met | [Metadata test](../../../tests/unit/chrona/app/test_agent_tools.py) checks all three command tools against their embedded schema constants; existing stdio registry-equality test carries the same descriptions. | — |

## Programme-level criteria (optional)

Local focused results (overlapping): related app/CLI/skill tests 328 passed;
metadata 3 passed; Store command tests 74 passed; real stdio tests 4 passed.
Import direction: 11 packages, 37 inward edges. Full local pytest is not repeated.
Conformance, official public-artifact audit, PR CI and exact review-containing
main three-OS release are pending; this is not release acceptance. No public
rendered-byte change is intended. Parent902 remains open for parked #815.
