# Implementation Plan — Draft System-Font Provider (#411)

## I411-1 Discovery and exact metrics

Add a typed system-font resolver port, fontconfig implementation, and a
resolved-face value.  Reuse the font importer metric extraction over the exact
resolved bytes.  Tests cover match, missing, substituted-family rejection,
malformed face, and unavailable bridge through a fake resolver.

## I411-2 Draft closure and renderer boundary

Add draft-only system configuration ingress and volatile host-font closure
state.  Inject resolved metrics/file into the normal draft pipeline.  PNG
uses the resolved file with restricted system fallback; SVG remains completed
geometry.  PDF/typeset reject system state.  Immutable closure and materialize
reject it structurally and at runtime.

## I411-3 Acceptance and publication

Add a local real-face fixture or test helper, draft SVG/PNG acceptance,
immutable rejection tests, and provenance/serialization structural checks.
Run focused and full tests, conformance, public materializer checks, then
publish source and review atomically.  Close #411 only after CI succeeds.
