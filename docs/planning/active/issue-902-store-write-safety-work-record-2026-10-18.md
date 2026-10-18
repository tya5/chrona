# Issue 902 — Store write safety work record (2026-10-18)

Status: design preparation only; #1679/PR1692 remains the active release.
Published baseline `ee99b2d78`. No item5 product code is changed.

## Scope and literal acceptance

[Issue902](https://github.com/tya5/chrona/issues/902), owner/reviewer order:
item5 → item3 → item2. Items4,814 and815 remain parked; completing this lane
does not silently close those requirements.

| Item | Literal remaining requirement | Literal acceptance |
| --- | --- | --- |
| 5, current | A multi-process write lock for one actual/snapshot Store. The authoring workspace already takes an OS file lock (`operational/authoring_commands.py`, fcntl/msvcrt), but a command line and a server writing one Store at once are not guaranteed. | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. Item 5 needs a two-process test that shows a lost update today and none after the fix. |
| 3, next | A revert path for a write. Today a revert is a compare-and-set write of an earlier revision's content through the Store. `LocalActualStore.undo` and `redo` return `None` (`src/chrona/commands/actual_commands.py:120`). | Same per-item stale-base, replay, no-overwrite and applicable MCP stdio acceptance above. |
| 2, after3 | `apply_authoring_command` as an MCP tool over the guided authoring workspace (`authoring-command-apply` and `workspace revision` exist on the CLI only), with the same write gate and honest annotations. | Same per-item stale-base, replay, no-overwrite and applicable MCP stdio acceptance above. |

## Item5 design plan

- **Authority:** [archived813 design §3.9/R7](../../archive/planning/issue-813-mcp-mutating-tools.md), [Spec15 §§3/7](../../specification/15-revision-store-adapters.md), and the shared CLI/MCP command path. The old active813 link is an archive move, not missing design. Item5 strengthens the explicitly deferred interprocess boundary; it does not add an approval step.
- **Verified code facts:** `LocalActualStore.write` compares cached state; separate instances can accept the same base sequentially. Mutable tips and `ReplayLedger.record` use independent read/check/replace sequences. Snapshot publication already uses exclusive immutable creation. Authoring's file lock is workspace-scoped, not this Store transaction.
- **Use cases:** two CLI/server processes mutate one Actual; identical commands race for replay; distinct Actual IDs share a ledger; snapshot capture races with its replay; a stale long-lived adapter writes after another process commits. Existing immutable revisions must remain untouched.
- **Decisions to complete before implementation:** choose the canonical Store-wide lock owner/path, transaction span, nested/thread acquisition policy, OS failure behavior, and the smallest shared platform primitive. Determine how direct adapter CAS participates without self-deadlocking inside the command transaction. Distinguish concurrent-operation safety from crash recovery; do not silently add journaling or a distributed-lock promise.
- **Architecture review:** Core/command meanings, opaque revision identities and immutable inputs stay unchanged. Persistence owns the lock; operational orchestration owns replay→mutation→record. CLI/MCP retain guards/envelopes and do not implement separate locks. Check the adjacent authoring aggregate lock and local Project adapter without expanding item5 beyond Actual/snapshot commands.
- **Data/migration:** prefer an adapter-private persistent lock file and unchanged revision/ledger formats; decide and document any observable diagnostics or failure changes. Do not alter planned data, render layers, source YAML or generated materializers.
- **Evidence:** spawn two independent adapters at one base, let A commit, then release stale B: current code accepts both, fixed code must preserve A and reject B without a revision or overwritten snapshot. Add overlapping command/ledger tests and applicable real stdio tests; require all three OSes in exact-main release. No timing target or sleep-based race proof.
- **Publication:** publish this plan; complete the selected design/specification and whole-architecture review; publish the item5 implementation plan; only then implement/test. One eventual item5 code PR after1679 is merged or explicitly parked. CI supplies full pytest/conformance/wheel/MCP gates; no duplicate local full suite. Items3 and2 receive their own design/implementation sections here before their code begins.

## Item5 selected design and architecture review

Spec15 §7 is normative; Spec66 §2.1 replaces its old explicit concurrency limit.
`storage/file_lock.py` shares only the existing fcntl/msvcrt mechanism with the
authoring aggregate lock; authoring keeps its existing diagnostic contract.
`storage/store_lock.py` owns canonical resolved/normcase root identity and the
persistent `.chrona-store.lock`. An RLock serializes threads before any reentrant
depth check; only the owning thread reuses the outer OS acquisition. Process
identity prevents inheriting a parent's reentrancy ownership. No lock deletion.

`operational.command_engine` owns the complete replay→fresh CAS→publish→record
transaction, with the registry root selected for captureSnapshot. It catches
only typed acquisition failures into its existing rejected result; an unrelated
post-publication I/O failure must not be misreported as a pre-write lock refusal.
`LocalActualStore` removes cached revision/content, reads immutable disk state
fresh, and uses the same coordinator for seed/CAS; `ReplayLedger.record` uses
that coordinator for direct callers. Immutable reads remain lock-free.

Whole-architecture review: storage owns the platform and exclusion mechanism;
operational owns transaction orchestration; command semantics and opaque tokens
stay unchanged. CLI/MCP continue through one engine and unchanged write/path
guards; no approval, schema, tool-set or protocol change. Reusing the authoring
kernel primitive does not merge workspace and Store transaction identities.
Generic Project editing, authoring crash recovery, malicious filesystem edits
and publication/ledger crash journaling stay outside this item. Migration adds
only the private lock file; existing tips, immutable revisions and ledger bytes
remain readable. Focused risks: nested self-deadlock, thread ownership, fresh
CAS, concurrent ledger loss, acquisition failure and same-root aliases.
