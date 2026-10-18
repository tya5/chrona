# Issue 902 — Store write safety work record (2026-10-18)

Status: item5 L1–L3 and local L4 implemented; PR/current-main release is pending.
Design/review `69273a1bf`, implementation plan `54b9ddd20` precede
code. Baseline `ee99b2d78`; #1679/PR1692 remains the priority release, with its
code explicitly parked during live CI. No902 product PR before1679 merges.

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

## Next-item baseline (design not yet selected)

- Item3: Spec10 §8 requires new-revision undo/redo with unsafe inverses rejected.
  Accepted replay results already retain before/after immutable references;
  investigate reusing that authority instead of a duplicate content journal.
  The closed command-request schema needs an explicit version/operation decision.
- Item2: reuse the authoring use case and CLI persistence adapters behind the
  existing MCP write gate. Adding a tool changes the tool-set contract. Current
  authoring code echoes commandId but has no durable replay; successful retry
  becomes stale-CAS rejection. Resolve that contract before claiming honest
  idempotent annotations or the item's replay acceptance. No item3/2 code yet.

## Item3 design plan

- Use case: an agent reverses an accepted Actual write, then reapplies its intent,
  without overwriting intervening changes or rewinding immutable revision history.
- Review Spec10 §8 against Store ownership (Spec15), command/reference contracts
  (Spec35), and CLI/MCP shared dispatch/write gates (Spec66). Preserve snapshot
  non-reversibility; do not extend this item to generic Project history.
- Resolve history authority, origin/revert eligibility, replay identity, current
  base/content checks, and missing/corrupt historical bytes. Existing ledger
  before/after refs can restore content, but its request hash cannot supply the
  original semantic intent required by redo. Decide the smallest durable intent
  representation and an explicit closed-command-schema migration before code.
- Order: selected contract/specification + whole-architecture review → implementation
  plan → shared engine/adapter/schema work → stale/replay/no-overwrite and real
  MCP stdio evidence → one reviewed release. Literal acceptance is listed above.

## Item3 selected contract (pre-code design branch; no product code)

Normative contract: [Spec35 §4.3](../../specification/35-operational-review-workflows.md),
connected by Specs10/66. Command v0.4 adds Actual revert/redo; MCP tool-set v0.5
admits them through existing tools, with unchanged gate/path/result contracts.
Fresh caller-base CAS and verified whole-state equality are independent guards.
The engine records canonical request intent in the existing ledger, not another
journal. Legacy records stay replayable/revertible; redo needs recoverable intent.

Implementation migration: remove `record_command` from ActualStore/core mutation
handlers, MemoryActualStore's process-local undo/redo and wrappers, and the
always-None LocalActualStore methods/history dictionary. Replace their tests
with durable engine coverage. Generic Project history is unchanged.

Architecture review: two independent reviews against Specs10/15/35/66 and the
shared parser/engine/MCP seams found and resolved exact-token rejection of safe
multi-command inverses, duplicated adapter history, missing legacy identity
checks and the MCP allowlist/version gap. All ancestry must match the same
Store/Actual; full identities are verified from immutable bytes, never trusted
from a ledger digest alone. Fresh-base CAS remains independent of state equality.
No unresolved architecture finding remains. Normative authority is Spec35 §4.3;
Spec10 and Spec66 connect the ownership and agent contract. Publish this design
before implementation planning. Item3 may pipeline as isolated WIP on the
verified public item5 implementation; its PR/release waits for item5 release. This branch
is separate from the item5 product/release branch, avoiding an unimplemented
tool-set claim in that release.

## Item3 implementation plan

Design/specification/architecture review `a79ab0307` is published on
`wip/issue-902-actual-history-design`. One coherent product PR after item5 release;
the following are owned implementation/test slices, not partial main releases.
WIP implementation may proceed during item5's publication wait; never merge
unimplemented item3 contracts into the separate item5 release branch.

| Slice | Owned files | Acceptance evidence |
| --- | --- | --- |
| H1 durable engine | New command v0.4 schema and required resource packaging/registry; `operational/resources.py`, `references.py`, `command_engine.py`; `commands/actual_commands.py` and corresponding tests | v0.3 still parses; verified canonical request retention; legacy replay/revert and explicit unavailable redo; new immutable revisions; original bytes unchanged; stale base, changed whole state, wrong Store/Actual, no-op/snapshot/revert origin, missing/corrupt/cyclic history, malformed retained request and command-ID reuse reject without writes. Shared semantic dispatch validates redo normally. Remove unused adapter history; migrate its tests rather than dropping coverage. |
| H2 agent exposure | `app/agent_tools.py`, tool registry/version descriptions, affected docs and MCP tests | Tool-set v0.5 admits inverse types only through existing tools. Disabled gate opens no files; paths stay contained; history diagnostics name the payload reference; CLI/tool Automation Results agree. Real stdio fresh/stale/replay/no-overwrite cases for revert and redo. |
| H3 release | Synthetic engine/CLI/MCP integration tests, Store process tests, literal review | Two ordinary writes → both reverted in order → both redone in order; repeat a revert/redo cycle; fresh processes reopen each step; inverse replay changes no bytes; concurrent inverse/normal writes serialize and reject unsafe state. Focused tests, schema packaging/equivalence and import checks; CI full three-OS pytest/conformance/wheel/MCP. No render policy or public materializer source change. |

Retain all item5 concurrency tests. Inspect any generated schema/inventory
evidence with its source and compare public artifact changes as a batch. Return
to design on a history/schema/ownership discrepancy. Item3 acceptance is the
literal row above; item2 and owner-parked requirements remain open.

### Item3 current implementation evidence

WIP implementation `c2984c018` follows design `a79ab0307` and plan `504478877`.
It is not merged or release-accepted. Independent review closed normalized
optional target identities, shared check/apply ancestry, malformed history,
snapshot/no-op classification and missing schema-packaging tests. Retained
requests are parsed against their closed schema and checked against their ledger
key as well as their hash; no unknown payload can silently become redo intent.

Focused batches (overlap, not summed): operational/command/tool/CLI/process223;
agent registry/Store reads293; final history/tool/concurrency64; schema/ledger61;
retirement/packaging45; adapter10; real history MCP/CLI-pointer batch5.
Schema equivalence passes with one declared v0.4 addition and three proven stale
S2 deltas retired; the five reported invalid documents are unchanged baseline
findings. Imports11 packages/37 edges inward. No public render policy/source
or canonical generated outputs changed. Remaining: current-main integration,
final CI/public evidence and exact-main release after item5 publication.

## Item2 design plan (no item2 product code)

- Baseline: CLI-only authoring use case/adapter (Spec51) echoes commandId but
  cannot replay an accepted retry; ordinary CAS lacks the aggregate OS lock.
  The existing transaction marker is recovery metadata, not accepted history.
- Scope: one new MCP `apply_authoring_command` tool through the same CLI/operational
  entry point, unchanged workspace containment and write gate. Decide tool-set
  v0.6, honest annotations, exact result/pointer contract and prospective migration.
- Design slices: pure prepare/validate versus operational commit ownership;
  durable accepted-request/result receipts within the existing workspace lock
  and transaction boundary; MCP exposure; architecture/migration review.
- Resolve before code: canonical request/target identity and ID collision;
  replay before stale-base checks; receipt/resource/workspace commit ordering;
  no-op commit identity; crash recovery and post-commit cleanup failures. Do not
  fake success from a CAS callback or add an unsynchronized second ledger.
- Evidence: literal item2 stale/replay/no-overwrite and real stdio acceptance
  above, restart/retry after later writes, changed-ID reuse, containment/gate,
  ordinary/materializing/no-op transactions, failure before/after commit and
  unchanged workspace/resource bytes on rejection. CI supplies the full gate.
- Publication: publish this plan, then Spec51/66 selected design and whole-
  architecture review, then implementation plan before code. One coherent item2
  release follows item3; design preparation may pipeline without mixing releases.
