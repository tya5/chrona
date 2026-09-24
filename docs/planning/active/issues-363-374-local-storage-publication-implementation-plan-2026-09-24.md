# Implementation Plan: Local Storage and Publication (#363, #374)

**Status:** Proposed

**Implements:** [Local Storage and Publication Design](../../design/issue-363-374-local-storage-publication-design-2026-09-24.md)
and its [architecture review](../../reviews/current/issues-363-374-local-storage-publication-architecture-review-2026-09-24.md)

## Entry conditions

The design establishes one encoded local snapshot layout, intentional
non-compatibility for pre-codec stores, a documented reservation visibility
contract, and an actionable Windows lock timeout.  No implementation may add a
second path codec, raw-layout fallback, renderer change, or OS-specific public
contract.

## S363-1 — Transactional store codec closure

Route `LocalTransactionalStore._persist()` and `_read_tip()` through
`snapshot_directory()`.  Keep its `tip.json` token and `local:<token>` revision
format unchanged.  Add focused transactional-store tests for write/restart,
parents, `baseline:<sha256>`-style tokens, percent-containing tokens, and a
Windows reserved token.  Add a negative fixture proving that a raw directory
with an otherwise valid tip is not a supported fallback.

**Files:** `src/chrona/storage/revision_store.py`, storage unit tests.

**Acceptance:** no production local snapshot adapter constructs a revision
directory from a raw token; the token remains opaque outside the storage path
adapter; all focused reader/materializer tests remain green.

## S363-2 — Intentional migration guidance

Add concise user-facing local-store guidance explaining that stores created
before the portable path codec must be re-created or re-captured.  It must link
the symptom to the ordinary immutable-reference failure path without promising
automatic recovery.  Add a documentation assertion where existing tooling
supports it.

**Files:** the current storage/authoring guide selected during implementation,
possibly its test or documentation checker.

**Acceptance:** a user can discover the break and recovery action without
reading implementation code; no migration or dual-layout reader exists.

## S374-1 — Shared exclusive-publication contract

Extract the common reservation-and-replace sequence into a low-level storage
publication helper.  Move `LocalBaselineRegistry.publish()` and CLI
`_write_result()` onto it without changing their public collision diagnostics.
Document the bounded final-name reservation interval in the helper and relevant
writer docstrings.  Test successful writes, duplicate rejection, cleanup after
failure, and the documented observation state through the helper rather than
duplicating race tests at each caller.

**Files:** a new low-level `src/chrona/storage/` helper, `storage/snapshots.py`,
`app/cli.py`, focused storage/CLI tests.

**Acceptance:** two callers share one protocol; no hard link or no-replace
rename claim is introduced; completed outputs, collision behavior, and cleanup
remain byte-compatible with existing callers.

## S374-2 — Actionable Windows aggregate-lock timeout

Add the operational contention translation selected by the design and preserve
lazy platform imports.  Carry `E_AUTHORING_LOCK_TIMEOUT` with its workspace and
lock-path retry detail through `apply_authoring_command()` as separate
`code`/`detail` result fields.  Test simulated Windows timeout, unrelated
operating-system failure propagation, POSIX lazy behavior, and the result
schema.

**Files:** `operational/authoring_commands.py`,
`usecases/authoring_commands.py`, authoring/CLI tests, generated diagnostic
inventory inputs if needed.

**Acceptance:** a rejected authoring command names the stable code, workspace,
and lock file; a combined exception string never becomes the diagnostic code;
no `msvcrt` dependency is imported on POSIX.

## S363/374-3 — Review and release gate

Run the focused storage, authoring, and CLI tests; full pytest; structural and
diagnostic inventory gates; public materializer byte checks; wheel build and
installed smoke; then inspect one consolidated generated-SVG/materializer diff
batch.  Push once per completed implementation/review phase and confirm the
Ubuntu/macOS/Windows GitHub CI matrix before closing both issues.

**Acceptance:** every design acceptance criterion is backed by current tests,
documentation, review evidence, and green three-platform CI.  The release
review explicitly verifies the absence of raw fallback and presentation-policy
changes.
