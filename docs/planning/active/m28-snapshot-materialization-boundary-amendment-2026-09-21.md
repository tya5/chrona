# M28 Snapshot Materialization Boundary Amendment

**Status:** Design complete — M28 amendment  
**Date:** 2026-09-21

## Decision

M28 does not introduce a snapshot materializer.

The current immutable resource boundary is LocalSnapshotReader: it reads the Render Context's pinned snapshot-ref, then that resource's pinned Project reference. The projection schedules that Project independently. This is the materialization required by M28, and it is read-only.

## Rationale

Creating a new copying/materializing command or an embedded schedule payload would add a second authority for historical plan data. That conflicts with Specification 38: a Snapshot Review Item must resolve from its named immutable schedule context and may not mean copied schedule data.

## Implementation-plan correction

R5 replaces “materializer” with “immutable-reader closure verification”. Conformance must verify:

- the Snapshot resource and nested Project are pinned independently;
- their revision may differ from the primary Project;
- their Project IDs match;
- the CLI schedules each Project independently; and
- no copied or latest snapshot payload is accepted.

This amendment does not restore any deleted Settings or legacy Theme contract.
