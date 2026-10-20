<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — inline commands (item 4)

Design and plan: `cfa3e22e3837aa62842a136452b2ff9645e24aba`;
implementation: `bf9ef2d85`. Current authority is the
[work record](../../planning/active/issue-902-store-write-safety-work-record-2026-10-18.md)
and [Spec66 §2.1](../../specification/66-agent-interface.md).
Exact-main release `39458042291` succeeded on
`073a38224718a0a17001a9bff58f3f9d95370688`, including Ubuntu, macOS, Windows,
MCP-floor, and newest-Python materializer reproduction. The
[official artifact audit](https://github.com/tya5/chrona/pull/1839#issuecomment-6295482682)
records all 50 SVGs and 50 Scenes byte-identical; only five existing
diagnostic-inventory source anchors changed.
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

## Release result

The exact-main three-OS release and required MCP/newest-Python checks passed.
All three literal criteria are met. Parent902 remains open for parked #815;
this review closes only item4 acceptance. No public rendered-byte change was
observed.
