# Issue 902 — Store write safety work record (2026-10-18)

Status: item5 PR1698 passed every product check in39094985183; readiness alone
failed after main advanced. Normal integration `30d957743` follows main
`e9432fb85` after B's1697 landing; that update changes CI/AGENTS only, not the
product code verified by107 focused command/adapter/process/docs tests and
11/37 inward imports. Final push requires successful derived-main on this exact
current tip. Design `69273a1bf` and plan `54b9ddd20`
precede code. #1679/#1680 are closed after exact-main39094741641 passed all
three OSes, public reproduction and MCP. Their archival/ledger update is an
independent commit in PR1698; separate docs PR1699 was superseded to avoid
another serial snapshot/sync cycle. This adds no item3/item2 product code.

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
- **Decisions:** the selected design below closes lock identity, transaction span, nesting, thread/OS failure behavior and platform reuse. Concurrent-operation safety is not crash recovery; no journaling or distributed-lock promise is added.
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

## Item5 implementation plan

One code PR only after1679 merges or is explicitly parked. These are review/test
slices, not partially safe main releases; publish their coherent implementation
and acceptance evidence together. Design `69273a1bf` precedes this plan.

| Slice | Files/owner | Focused acceptance |
| --- | --- | --- |
| L1 kernel/coordinator | `storage/file_lock.py`, `storage/store_lock.py`, existing authoring wrapper | Persistent canonical-root file; nested same-thread reuse, other-thread/process exclusion, exception release and typed acquisition failure. Existing authoring Windows/POSIX diagnostics unchanged. |
| L2 fresh CAS | `commands/actual_commands.py`, direct adapter tests | Remove cache authority; seed/write under coordinator; read fresh disk. Two spawned adapters at one base: A commits, stale B conflicts, A remains current, no B revision and no overwritten immutable bytes. Demonstrate failure on baseline before fix. |
| L3 command transaction | `operational/command_engine.py`, `operational/references.py` | Lock before replay lookup until accepted result recorded; direct ledger RMW participates; destination registry lock for snapshots. Stale-base, same-ID replay, conflicting-ID reuse, no overwrite, concurrent distinct ledger entries and snapshot name collision. |
| L4 release | `tests/integration/test_store_write_lock.py`, existing command/authoring/MCP stdio tests, literal review | Deterministic spawn/Event overlap proves OS serialization separately from stale-cache repair; no sleep-based success criterion. Applicable real MCP stdio stale/replay/no-overwrite tests, import/diagnostic gates and conformance. CI supplies full three-OS pytest/wheel release on exact main containing review. |

Use the new worktree's own venv. No render-materializer rerun is needed for this
storage-only slice unless dependency review reveals render-visible behavior.
No revision/ledger schema migration or generated-output edits are planned.
Acquisition errors are mapped narrowly; a simulated publication I/O failure
must retain its original failure rather than claim a safe pre-write rejection.

## Current item5 evidence

- Regression `tests/integration/test_actual_store_concurrency.py` (`605232991`):
  two spawned adapters open one base, then Event handshakes release A before B.
  Baseline fails in0.95s: stale B returns `actual:3:84aa7f2ec6b7`, losing A.
  L2 `9dcf22c16` passes: B conflicts, A stays current, every Store file and
  immutable revision byte remains unchanged after A. Both workers exit cleanly.
- L1 `a4c7fe08c`: canonical/reentrant thread/process/fork, acquisition/body/unlock
  errors and interrupted-acquisition cleanup tests pass (11). Authoring wrapper
  preserves its platform diagnostics (39 existing tests).
- L2 adapter/address/concurrency batch:504 passed. Focused operational/authoring/
  lock batch:67 passed; transaction errors/direct concurrency batch:18 passed
  (overlapping batches, not summed). Import direction:11 packages/37 edges inward.
- L3 `ab376c78e`: engine replay→publication→record exclusion, concurrent ledger
  records, snapshot replay/name collision and registry-vs-input-root tests pass.
  A writer paused after publication blocks a competitor's replay lookup until
  durable recording completes; then exactly one mutation and one replay result.
  Independent review confirms transaction and failure ownership. Combined focused
  engine/reference/Store/concurrency batch:23 passed.
- MCP stdio Store gate/stale/replay/no-overwrite/path checks and two render parity
  checks:6 passed. An initial broader run had63 pass/2 render failures because
  this WT lacked render extras; installing `.[render]` plus the Noto provider in
  its own venv resolved both. No product workaround or weakened assertion.
- Pending: current-main integration, CI/release and literal acceptance review.

## Item5 literal acceptance review (release pending)

Implementation `ab376c78e` with L1 `a4c7fe08c`, L2 `9dcf22c16`; public WIP
`wip/issue-902-store-write-safety`. This reviews item5 only; items2/3 and parked
4/814/815 remain open. No issue closure or current-main release claim.

| Literal item5 acceptance | Disposition | Direct evidence |
| --- | --- | --- |
| Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met (item5) | `tests/integration/test_actual_store_concurrency.py`, `test_store_write_lock.py`, `test_store_transaction_span.py`; MCP stdio `test_with_allow_write_an_intake_and_a_capture_are_applied_and_equal_the_command_line` and `test_stale_replayed_and_overwriting_commands_are_refused_over_stdio_and_nothing_is_overwritten`. Focused outcomes recorded above; not evidence for items2/3. |
| Item 5 needs a two-process test that shows a lost update today and none after the fix. | met | Committed regression605232991 fails on baseline; the same test passes after9dcf22c16, rejecting the stale writer with every post-A Store file byte unchanged. |
| Required release gate on current main containing this review. | not met | Current-ready-base PR/CI, exact-main three-OS full pytest/conformance/wheel/MCP and publication verification remain pending. |

Structural review: engine owns the whole replay/CAS/publication/record scope;
storage owns canonical-root/thread/process exclusion and raw OS locking;
authoring retains its own workspace lock identity/diagnostics. No second ledger,
renderer behavior, schema migration, approval or crash-atomicity promise added.
Acquisition errors reject before mutation; publication/unlock errors remain raw.

Official artifact12124072125 (source96e657289, CI39094985183), archive SHA-256
`235288f64f486b80fd2422bc7b9a96ad99ae3a889899db95db35d503614b6c9c`:
all50 SVGs/50 Scenes byte-identical to final reviewed1679 artifact; no added or
removed paths. Only two inventories change, for source coordinates and two
helper-owner names. All seven other reports are unchanged. Final current-base
CI and exact-main release remain required; the old failed ready gate is not waived.

## Later items (not part of the item5 release)

- Item3 design/review `a79ab0307`, implementation plan `504478877` and code
  `c2984c018` are published separately at `d0048bf2c` on
  `wip/issue-902-actual-history-design`. That branch owns its current contract and
  focused evidence; its PR/release follows item5. It is not yet main functionality.
- Item2 design `cdf0289f8`, plan `fa31cc79c`, code `fa831e384` and review
  `0b79e65a0` are separate `wip/issue-902-authoring-design` work. That branch
  owns durable authoring replay and MCPv0.6; neither is included in item5.
  Its PR/release follows item3. Parked4/814/815 still remain open.
