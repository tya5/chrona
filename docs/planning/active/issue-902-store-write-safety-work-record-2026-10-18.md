# Issue 902 — Store write safety work record (2026-10-18)

Status: item5 PR1698 follows ready main `8e25a4232` after B's1695 landing.
CI39099136587 passed every product check; readiness failed when main advanced.
The final official artifact12126176185 retains all50 SVG/50 Scene bytes; only
diagnostic source coordinates differ from the prior snapshot. Current-base
Store/engine/process tests pass21; earlier focused107 and inward imports11/37
also passed. Final-head CI and exact-main release remain required. Design
`69273a1bf` and plan `54b9ddd20` precede code.
#1679/#1680 are closed after exact-main39094741641 passed all
three OSes, public reproduction and MCP. Their archival/ledger update is an
independent commit in PR1698; separate docs PR1699 was superseded to avoid
another serial snapshot/sync cycle. Item3 code `c2984c018` and item2
code/review `fa831e384`/`0b79e65a0` remain unreleased; this branch is not a main
release claim. Merge/release order remains5→3→2. Item3 PR may open only after
item5 merges and derived-main is ready; its merge waits for item5's successful
full release. Item2 PR may open only after item3 merges and derived-main is
ready; its merge waits for item3's successful full release. Any predecessor
release failure remains that predecessor owner's priority. Board454 is
reviewer-owned and unchanged.

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
| Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met (item5) | `tests/integration/test_actual_store_concurrency.py`, `test_store_write_lock.py`, `test_store_transaction_span.py`; MCP stdio gate/stale/replay/no-overwrite checks recorded above. Not evidence for items2/3. |
| Item 5 needs a two-process test that shows a lost update today and none after the fix. | met | Regression605232991 fails on baseline and passes after9dcf22c16, with all post-A Store files unchanged. |
| Required release gate on current main containing this review. | not met | Final current-ready-base PR CI and exact-main three-OS release remain pending. |

Engine owns the complete replay/CAS/publication/record scope; storage owns root/
thread/process exclusion. Authoring keeps separate workspace identity. No new
ledger, renderer behavior, schema or crash-atomicity promise. Body/unlock errors
remain raw; acquisition failures happen before mutation.

Official artifact12124072125 (96e657289, CI39094985183), archive SHA-256
`235288f64f486b80fd2422bc7b9a96ad99ae3a889899db95db35d503614b6c9c`:
all50 SVGs/50 Scenes unchanged from final1679; no added/removed paths. Only two
inventories change, for source coordinates and two helper-owner names; seven
other reports unchanged. This does not waive final CI/release.

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

## Item3 selected contract

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
before implementation planning. Item3 remains isolated WIP on the verified
public item5 implementation. Its PR may open after item5 merges and derived-main
is ready, concurrently with item5's full release; item3 merge remains blocked
until that release succeeds. This branch is separate from item5's product and
release acceptance, avoiding an unimplemented tool-set claim in that release.

## Item3 implementation plan

Design/specification/architecture review `a79ab0307` is published on
`wip/issue-902-actual-history-design`. One coherent product PR may open after
item5 merges and derived-main is ready; item3 merge still waits for item5's
successful full release. The following are owned implementation/test slices,
not partial main releases. WIP implementation may proceed during item5's
publication wait; never merge unimplemented item3 contracts into the separate
item5 release branch.

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
or canonical generated outputs changed. Ready-main integration `499d2ad27`
passed99 focused command/adapter/CLI/process tests, three real MCP history
tests and an independent11-test history/concurrency audit; no conflict or new
architecture gap. Remaining: item5 final-head/current-ready-base CI and full
release. Item3 PR may open after item5 merges and derived-main is ready, but
item3 merge remains blocked until item5 full release succeeds. This changes PR
timing only; acceptance is unchanged.
Following ready `9e224db6c` and predecessor review `950d79001` changes no item3
engine/schema code;31 focused history/concurrency/documentation cases pass.

## Item2 design plan

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
- Publication: design/implementation preparation may pipeline on its isolated
  branch. Item2 PR opens only after item3 merges and derived-main is ready; the
  item2 merge waits until item3's successful full release. Any item3 release
  failure remains its owner's priority and blocks item2 merge. This changes PR
  timing only; item2 acceptance is unchanged.

## Item2 selected design and architecture review

Normative authority: Spec51 §4.2 and Spec66 §2.3/tool-set v0.6. Keep the
existing command/result v0.1 and return the exact durable result on retry, with
no new replay flag. Canonical workspace identity also unifies lock/receipt scope;
alias callers must name the canonical filename in `target.path`.

Use case preparation produces complete validated candidate bytes, next content
identity and an opaque exact result, without canonical writes. One injected
transaction port coordinates both CLI/MCP; it invokes preparation under the
workspace lock and owns receipt/recovery/commit. It never interprets authoring
operation payloads or presentation types. Remove the old two-CAS-callback path,
not preserve it as a compatibility bypass. Update the tool import-direction
guard for this one named port, retaining all other layer restrictions.

Whole-architecture questions: Spec10 idempotent intent versus authoring-local
content revisions; Spec15 Store locks versus the separate workspace scope;
Spec51 prepare/materialization proof and publication ownership; Spec66 gate,
containment, honest annotations and exact result parity. Receipts are accepted
history, the marker is transient recovery, and existing materialization receipts
remain provenance. No duplicated ledger, new workspace schema or renderer rule.
Two independent architecture reviews found no remaining contract blocker.
Resolved findings: explicit no-op receipt commit, committed-marker replay when
cleanup fails, hashed/verified receipts and owned-output recovery, legacy marker
fail-closed migration, canonical alias refusal, and gate before file reads.
The aggregate writer must extend ownership/recovery to receipt plus resources;
its old single-directory rollback cannot be reused unchanged. Implementation
must not delete prior receipts or post-commit resources, or claim CAS success
before publication. Publish this design before finalizing its implementation plan.

## Item2 implementation plan

Selected design/whole-architecture review `cdf0289f8` precedes this plan.
Use one neutral `storage.file_transaction.PreparedFileMutation(files,
result_revision, result)` with named byte candidates, next workspace identity
(null for refusal) and an opaque exact result.
The use case supplies `prepare(canonical_path, current)` and
`reject(code, observed_identity, detail)` and
`verify_receipt(request, result, before_identity, after_identity)` callbacks to
`operational.authoring_commands.transact_authoring_command`.
It returns the prepared/stored result; the Engine never imports authoring types
or interprets operation payloads. CLI/MCP inject this same transaction port into
the use case. Remove the old public CAS-callback wiring, not emulate it.

| Slice | Owned files | Acceptance evidence |
| --- | --- | --- |
| A1 prepare | `usecases/authoring_commands.py` and use-case tests | Validate full ordinary/materializing candidates, receipt command/result schemas/identities and exact results before publication; preserve proof, closure, overrides and failure details. No canonical writes or fake successful CAS. Canonical target mismatch is actionable; migrate callback tests without losing stale/collision coverage. |
| A2 transaction | `storage/file_transaction.py`, `operational/authoring_commands.py` and persistence/recovery/process tests | One lock for every command; durable exact replay before base comparison, changed-ID reuse, verified receipt corruption/path guards, no overwrite. Marker distinguishes changed workspace/no-op commits; injected failures/restarts before/after publication preserve old or fully committed state, including legacy recovery and post-commit cleanup/replay. Earlier receipts/resources survive. |
| A3 front ends/release | `app/cli.py`, `app/agent_tools.py`, import guard, registry/CLI/MCP tests and literal review | Tool-set v0.6/new tool and honest annotations; gate before missing/malformed/escaped files open; canonical/symlink scope; exact CLI/tool results, stale/replay/no-overwrite over real stdio. Run focused tests per owner, then combined tests and planned CI full three-OS/conformance/wheel/MCP; inspect official materializer deltas as a batch. No renderer policy/source change intended. |

Implement as isolated WIP while predecessor releases run; one coherent item2 PR
may open after item3 merges and derived-main is ready, but item2 merge waits for
item3's successful full release. Do not publish partially safe main slices.
Return to design before addressing any new transaction/schema/layer contract
gap. Acceptance is the literal item2 row above; parked4/814/815 remain open.

## Item2 implementation review

Code: `fa831e384`, following design `cdf0289f8` and plan `fa31cc79c`.
CLI/MCP share the preparation/transaction port; no writer compatibility bypass
remains. Engine retains no authoring operation/presentation interpretation.
Canonical filename spelling is preserved; case normalization affects identity
only, and staging identity includes workspace scope as well as command ID.
Independent reviews found and resolved committed-cleanup replay and marker-to-
receipt cross-check gaps. Owned-stage validation preserves unexpected files.
No renderer/schema/source-YAML or generated artifact changes in this slice.

| Literal item2 acceptance | Result | Direct evidence |
| --- | --- | --- |
| MCP tool over guided authoring workspace, same write gate and honest annotations | met locally | `test_agent_authoring.py`, `test_authoring_stdio.py`: both paths contained, gate before reads, writer/destructive/idempotent annotations, exact CLI result, canonical aliases and failed preflight envelopes. |
| Own stale-base, replay and no-overwrite tests | met locally | Operational authoring/recovery tests and `test_authoring_command_transaction.py`: restart/after-later-write replay, changed-ID refusal, corrupt receipts/markers, no-op, rollback, replace-then-raise acceptance, two spawned writers. |
| MCP stdio test where it is a tool | met locally | `tests/mcp/test_authoring_stdio.py`: enabled/disabled server, exact retry, stale base and ID reuse without overwriting receipts/workspace. |
| Required release evidence | not met | Item5 then item3 must release first; item2 PR CI, exact-main three-OS/conformance/wheel/MCP and official materializer comparison remain pending. |

Verification: combined focused authoring/containment/registry/CLI/Store/MCP
batch **1010 passed**; final recovery/helper migration **489 passed** and
case/staging/process batch **58 passed**. These batches overlap, not additive.
`tools/check_import_direction.py`: 11 packages/37 inward edges; diff check clean.
Full local pytest/public-materializer reruns deliberately delegated to CI.
Current-base integration of predecessor `64c8a6094`/ready `9e224db6c` preserves
item2 product code;40 focused history/authoring/process/stdio/docs cases pass.
Design `cdf0289f8`, plan `fa31cc79c`, code `fa831e384` and review `0b79e65a0`
are on `wip/issue-902-authoring-design`; that branch owns durable authoring/MCPv0.6.
Item2 PR may open after item3 merges and derived-main is ready; item2 merge waits
for item3's successful full release. Parked4/814/815 remain open.
