# #257, #308, and #258 Acceptance-Evidence Design Correction

**Status:** Accepted correction  
**Date:** 2026-09-23

## Decision

The audit findings are acceptance-proof omissions, not a new product design.
Their correction is limited to executable evidence and a small CLI adapter
extraction for #257.

`chrona schedule` receives one pure serialization helper that projects an
already completed successful scheduling result into its existing JSON shape.
It does not schedule, diagnose, or select presentation data.  Rejection stays
on the existing diagnostics route.

Progress-fill tests use the established Draft ingress and completed render
pipeline.  They cover the two declared data sources and optional omission
semantics; they do not add a fallback, host inference, or target-local mark.
`actual.progress` remains owned by Actual Set v0.2.

Typeset Draft tests exercise the existing CLI grammar and typed
`TypesetterIdentity`.  They do not add a descriptor resource, executable probe,
or immutable Context override.

## Whole-architecture review

The correction preserves all directions of authority: CLI serializes or parses
invocation input; Project/Scheduler and Actual own facts; View selects intent;
Layout owns geometry; Scene projects completed primitives; adapters serialize.
Temporary fixtures remain outside the public materializer corpus.  Therefore
no specification or implementation design revision is required before the
evidence work proceeds.
