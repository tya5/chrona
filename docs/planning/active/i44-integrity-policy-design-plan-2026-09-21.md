# Issue 44 Integrity Policy Design Plan

**Issue:** #44
**Status:** Active

## Objective

Define when immutable revision references require an explicit content identity, without weakening third-party package integrity or write-time optimistic locking.

## Steps

1. Audit reference schemas, readers, stores, Context closure, extensions, baselines, and command operations.
2. Define optional pin, store-required integrity, and caller-required integrity semantics.
3. Specify computed identity propagation and diagnostics.
4. Review against reproducible examples, release artifacts, snapshots, and #38.
5. Publish completed design before implementation planning.
