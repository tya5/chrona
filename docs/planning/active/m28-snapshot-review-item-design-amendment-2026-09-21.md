# M28 Snapshot Review Item Design Amendment — 2026-09-21

**Status:** Design correction complete; implementation planning is authorized.

The Review Item model correctly generalizes a Snapshot as an explicit item source, but
the current Render Context v0.5 resolver does not load `inputs.snapshot`. A Snapshot
Review Item would therefore be an undeclared runtime dependency. M28 must introduce a
versioned v0.6 Render Context closure:

1. `inputs.snapshot` is a typed immutable `snapshot-ref` resource reference;
2. the resolver loads that resource, then its nested immutable Project reference;
3. primary and snapshot schedules are independently derived and their Project IDs must
   match; and
4. the closure records distinct immutable revisions rather than falsely requiring a
   historical Snapshot Project to share the primary-context revision.

This correction does not add a live branch, filesystem fallback, or copied schedule
state. It makes the existing immutable Snapshot contract reachable by the new generic
Review Item source.
