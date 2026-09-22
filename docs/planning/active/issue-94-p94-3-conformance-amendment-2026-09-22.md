# Issue 94 P94-3 — Conformance Amendment

**Status:** Design correction required before P94-3 merge.  **Reason:** the
P94-3 deletion candidate exposed release-conformance fixtures that still name
deleted, non-product library sketches as evidence.

## Finding

`current-profile-release-acceptance-v0.2.yaml` cites the retired optional
Actual-intake adapter, interactive client, and output coordinator for UC-03,
UC-09, and UC-13.  Those are not the current public paths.  The same repository
also has an M13 successor-release acceptance schema, manifest, and validator
which make a release claim for the DateTime, capacity, collaboration, extension,
and output sketches being deleted in P94-3.

Retaining either set after deletion would make conformance fail or, worse, would
restore evidence by claiming an inactive library path is product delivery.

## Correction

1. Keep the current-profile release manifest, but bind its accepted rows to
   executable current paths: Actual commands/closure for UC-03, immutable
   Render Context materialization for UC-09, and the completed Scene SVG route
   for UC-13.  Its accepted/excluded use-case set does not change.
2. Retire the M13 successor-release acceptance **as an executable release
   conformance claim**: delete its manifest, schema, validator, and invocation
   from `conformance/run_conformance.py`.  The use-case catalog and proposed
   specifications remain design evidence; they do not claim a shipped release.
3. Do not delete independent schema fixtures merely because they model a future
   design.  P94-3 is deleting inactive executable modules and their false
   release claim, not revising the product roadmap.

## Verification

The P94-3 implementation PR must run conformance after this correction, prove
that release evidence paths exist and exercise current product boundaries, and
retain zero staged/unreachable modules.  It must still pass full pytest, all
five public materializers, and produce no generated SVG diff.
