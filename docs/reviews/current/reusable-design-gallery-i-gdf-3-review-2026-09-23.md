# I-GDF-3 Local Acquisition and Lock Review

**Date:** 2026-09-23  
**Scope:** local package acquisition, cache verification, package lock, and CLI
**Decision:** Accepted

## Architecture conformance

`chrona package acquire` is the sole operation that reads a selected local
package root and populates the deterministic local cache.  It validates source
bytes before copying, validates copied bytes again, then atomically writes a
provider-neutral lock.  The lock holds only immutable package/manifest/preset/
resource identities and compatibility declarations; it never serializes the
cache path, source root, registry state, or a mutable selector.

Locked verification derives a local cache lookup solely from lock identity and
then revalidates every byte.  It has no network or source-directory fallback;
missing bytes diagnose `E_PACKAGE_OFFLINE_UNAVAILABLE`.  No renderer or
normalizer imports the acquisition module in this slice.

## Evidence

- Acquisition tests prove provider-neutral lock output, successful locked
  verification, and offline unavailability diagnostics.
- Existing package tamper/authority tests remain green.
- CLI regression and schema inventory tests pass (36 focused tests total).

I-GDF-4 is the first slice allowed to consume this lock in guided authoring.
