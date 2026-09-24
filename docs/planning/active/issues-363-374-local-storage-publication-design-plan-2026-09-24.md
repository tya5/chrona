# Issues #363 and #374 — Local Storage and Publication Design Plan

**Status:** Proposed

## Purpose and dependency order

This programme closes the remaining local-storage portability boundary before
any public command adopts `LocalTransactionalStore`.  It deliberately treats
#374 as a completion slice of #363, rather than introducing a second storage
authority or a platform-specific repair path.

```text
D363/374-1 storage and publication design
  -> whole-architecture review
    -> implementation plan
      -> S363-1 safe transactional snapshots
        -> S374-1 actionable Windows lock and invisible publication
          -> S363/374 release gate
```

Every design, implementation, and review phase is published before the next
phase starts.  The following diagnostic-quality work in #371 may enrich
`E_STORE_REFERENCE`, but it is not a prerequisite for making the storage
layout and migration boundary explicit.

## Published facts

- `snapshot_directory()` is the sole Windows-safe, injective representation of
  opaque immutable revision tokens used by `LocalSnapshotReader`,
  materialization, and Actual storage.  It maps a token to one `revision-`
  prefixed percent-encoded directory component.
- `LocalTransactionalStore` is a dormant local persistence adapter.  It still
  creates and reads `root/<raw token>/project.json`, so it violates that
  adapter boundary even though no public command currently reaches it.
- The #359 reservation-and-replace implementation preserves no-overwrite
  semantics, but a reader can observe a newly reserved destination as an empty
  file before replacement.  It is used for baseline resources and CLI result
  artifacts.
- The authoring aggregate lock uses `flock(LOCK_EX)` on POSIX and
  `msvcrt.locking(LK_LOCK, 1)` on Windows.  The latter has a bounded retry and
  can surface a raw operating-system exception without workspace or lock
  identity.
- Chrona is pre-release.  A raw-directory local store is not a compatibility
  contract, and a silent dual-layout reader would create ambiguous persistence
  authority.

## Design questions to close before implementation

1. Define one transactional-store on-disk record layout that uses the shared
   snapshot-path codec while retaining the opaque external `local:<token>`
   revision value unchanged.
2. Define the explicit pre-codec migration outcome: old raw directories are
   unsupported and must be re-captured/re-created.  Identify the user-facing
   guidance location and ensure no compatibility reader or fallback lookup is
   introduced.
3. Decide the publication contract for an exclusively reserved destination.
   It must either use a portable no-replace publication primitive that prevents
   an observer from seeing an empty final name, or explicitly document the
   bounded reservation window.  The decision must cover both baseline and CLI
   result writers, not only one call site.
4. Define a platform-neutral operational lock result.  A Windows contention
   timeout must become a stable diagnostic carrying the workspace and lock
   location, while POSIX retains its declared wait behavior.  It must not leak
   platform imports or platform exception types into use cases.
5. Establish focused, simulated-Windows and public-command evidence for token
   safety, migration rejection, publication visibility, and lock contention.

## Planned design work

### D363-1 — Transactional snapshot layout and migration contract

Publish an English design that makes `snapshot_directory(root, token)` the
only local snapshot-directory constructor for all production local snapshot
adapters, including `LocalTransactionalStore`.  The record contents remain
`project.json`, `parents.json`, and `tip.json`; only the filesystem encoding of
the opaque internal token changes.  The design must state exactly how `tip` is
read and how the external revision remains `local:<token>`.

The design must explicitly reject both raw-directory fallback lookup and data
migration.  It must add clear user guidance that local stores created before
the portable codec must be re-created, and identify #371 as the later owner of
the actionable detail for a resulting `E_STORE_REFERENCE`.

### D374-1 — Atomic visibility and advisory lock contract

Publish a shared publication helper design for exclusive output paths.  A
portable no-replace rename primitive is not available through the supported
Python/filesystem baseline: a hidden reservation followed by ordinary rename
would reopen the no-overwrite race, while replacing a final-name reservation
retains a bounded empty-file window.  Therefore this programme chooses the
existing reservation-and-replace algorithm and makes that narrow visibility
window explicit in its public writer contract.  It preserves the existing
no-overwrite race result and cleanup guarantees without pretending that an
OS-specific primitive is portable.

Define an operational `E_AUTHORING_LOCK_TIMEOUT` diagnostic (or an accepted
single canonical successor) with structured workspace and lock-path detail.
The adapter catches only the Windows bounded-contention outcome; unrelated I/O
failures retain their appropriate failure path.  POSIX's indefinite advisory
wait remains deliberate and documented rather than emulated with a new polling
policy.

### D363/374-2 — Whole-architecture review

Review the accepted design against immutable-reference resolution, revision
identity, Operational/use-case/CLI failure translation, authoring aggregate
atomicity, baseline publication, materializer reads, and Windows portability.
The review must reject:

- a raw-token directory constructor outside `snapshot_paths.py`;
- dual raw/encoded directory lookup or silent migration;
- a destination-name placeholder visible to readers;
- renderer, Context, Layout, Scene, or revision-token semantic changes;
- platform exception types crossing the operational boundary.

## Implementation-plan requirements

The subsequent plan must contain independently reviewable and publishable
slices:

1. route transactional persistence and restart reads through the codec; add
   `baseline:<sha256>`-style, reserved-device-name, and restart round trips;
2. document the intentional pre-codec break and prove the raw layout is not
   read as a fallback;
3. consolidate the two reservation-and-replace call sites behind the accepted
   documented publication contract and test exclusive races plus the stated
   reader-visible condition;
4. add the named Windows contention diagnostic, simulated adapter tests, CLI
   / authoring result propagation, and the platform-semantics documentation;
5. run focused tests, full pytest, structural/diagnostic gates, public
   materializer checks, wheel smoke, and Ubuntu/macOS/Windows CI; review the
   generated materializer evidence only once as one batch.

No slice may leave an existing materializable Context unreadable.  No migration
or compatibility reader may be added merely to retain a pre-codec local-store
directory.

## Acceptance and release gates

- Every production local snapshot adapter uses the common codec and retains
  its opaque externally visible revision token.
- Safe-token round trips cover baseline-style, percent-escaped, and
  Windows-reserved inputs; raw pre-codec directories are rejected as designed.
- Baseline and CLI result writers document their bounded final-name
  reservation window and duplicate publication remains rejected.
- Windows aggregate-lock contention produces a stable, actionable diagnostic
  naming the workspace and lock; POSIX behavior is documented.
- Migration impact is documented where local-store users look.
- Focused and full tests, all structural gates, public materializer byte
  checks, wheel smoke, and all three GitHub CI platforms pass before closing
  #363 and #374.
