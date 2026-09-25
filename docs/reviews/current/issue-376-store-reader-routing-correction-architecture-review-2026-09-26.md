# Architecture Review — Store Routing Correction for #376

**Decision:** Accepted for implementation.

The correction restores, rather than broadens, the existing immutable
authority model.  Revision token form identifies the storage representation:
ordinary Context closure revisions are resolved by `LocalSnapshotReader`, and
the `baseline:` namespace reserved by `LocalBaselineRegistry` remains owned by
the baseline publication adapter.  The Store configuration stays one root;
the reader does not inspect mutable source or synthesize a fallback copy.

This keeps `copy_context_closure`, Context semantics, and materializer
topology unchanged while making their existing ordinary-revision closure
readable through the configured local Store.
