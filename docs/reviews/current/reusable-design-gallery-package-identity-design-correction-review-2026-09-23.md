# Presentation Package Identity Design Correction Review

**Date:** 2026-09-23  
**Scope:** Specification 62 section 2 aggregate content identity
**Decision:** Accepted correction before I-GDF-2 implementation

## Finding

The proposed manifest stores `package.contentIdentity`, while the original
wording said the package digest covered its canonical manifest.  Hashing the
literal complete manifest would include the digest being computed and has no
finite definition.

## Correction

The aggregate digest now frames canonical manifest data with only its own
`package.contentIdentity` omitted, followed by safe-path-ordered exact member
bytes.  Per-member SHA-256 identities remain literal-byte checks.  This makes
the aggregate reproducible without using cache paths, filesystem metadata, a
registry response, or a mutable checkout identity.

## Architecture review

The correction is confined to package acquisition/verification.  It adds no
renderer, Context, Layout, Scene, or package resolver authority; the lock will
record the resulting immutable aggregate value.  It is therefore consistent
with the closure, offline, and one-canonical-source boundaries.  I-GDF-2 may
resume against this corrected definition.
