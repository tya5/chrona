# Issue 902 — MCP command work record

Status: items5/3/2 and consolidated814 are released. Item4 merged in
[PR1839](https://github.com/tya5/chrona/pull/1839) at
`b6b1738c4829f688b63edf03951ca9b97631b40b`; exact ready main
`073a38224718a0a17001a9bff58f3f9d95370688` is published.
[Release39458042291](https://github.com/tya5/chrona/actions/runs/39458042291)
must complete before item4 is release-accepted. Parent902 stays open for parked
#815 (HTTP and other later options); board454 is read-only.

## Released predecessors

| Item | Current acceptance authority |
| --- | --- |
| 5: Store process lock | [Review](../../reviews/current/issue-902-store-write-safety-acceptance-review-2026-10-18.md); exact-main release39105269292. Specs15/35 own persistence/transactions. |
| 3: Actual revert/redo | [Review](../../reviews/current/issue-902-actual-history-acceptance-review-2026-10-18.md); release39108421823. Spec35 owns history/replay. |
| 2: Authoring MCP | [Review](../../reviews/current/issue-902-authoring-acceptance-review-2026-10-18.md); release39119120797. Spec51 owns preparation and the durable transaction. |
| Consolidated814: real-host trial | [Transcript/review](../../reviews/current/issue-902-agent-host-transcript-2026-10-20.md); release39382911887. The separately filed defect1807 is closed. |

## Item4: inline commands

Authority: [reviewer6294800291](https://github.com/tya5/chrona/issues/902#issuecomment-6294800291).
Design/architecture/implementation plan was published before code in
`cfa3e22e3837aa62842a136452b2ff9645e24aba`.
The additive tool-set v0.8 contract is [Spec66 §2.1](../../specification/66-agent-interface.md).

| Literal acceptance | Evidence |
| --- | --- |
| An MCP stdio test where an agent with no file access validates a plan, applies an inline edit, reverts it and renders, using only tool calls. | MCP-only workspace lifecycle verifies the returned embedded SVG and creates no command file. |
| Inline and path forms produce identical revisions for the same command. | Equivalent Store/authoring fixtures compare results, revisions and stored bytes; mixed-form replay and stale/reused-ID/no-overwrite controls remain. |
| The tool descriptions state both forms, with the exact version literal (as in #1807). | Registry metadata tests compare all three command tools with their embedded schema constants; real stdio lists the same registry. |

### Design and whole-architecture review

Only the Store input boundary needed implementation: authoring inline already
existed. Both Store forms use the packaged v0.3/v0.4 schemas, the same parser
normalization and `run_store_command`; input form/path is absent from canonical
request and replay identity. Store configuration stays path-only and contained.
Write-gate-before-open, lock/replay/CAS/exclusive publication and authoring's
durable transaction remain their owners' responsibility (Specs09/10/35/51).
Layout, Scene and adapters are unchanged. No schema migration, new writer,
Project syntax, HTTP transport or compatibility bypass is introduced.

### Implementation and remaining gate

Code `bf9ef2d85`, final PR head `ca1c9f342ae36d2a2e4b626656a0b15c78cc9fd1`.
Focused batches overlap: related328, metadata3, Store74 and stdio4 passed.
PR CI39454479470 passed all applicable checks.
The [official audit](https://github.com/tya5/chrona/pull/1839#issuecomment-6295482682)
records 109 paths: all50SVG/all50Scene and8/9 reports byte-identical; only five
existing diagnostic-inventory source anchors changed. This disposes of the
source-only local inventory-staleness result without authoring generated files.

[Literal review](../../reviews/current/issue-902-inline-commands-acceptance-review-2026-10-21.md)
owns row evidence. Next: verify the exact-main three-OS pytest/conformance/wheel,
MCP and newest-Python release, update this status/review once, then accept item4.
No parent closure or #815 completion is implied.
