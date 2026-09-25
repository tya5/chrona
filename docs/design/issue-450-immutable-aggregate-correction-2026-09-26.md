# Design Correction — Immutable Aggregate Diagnostics (#450)

The compatibility promise applies when collection produces exactly one
diagnostic.  It does not permit an invalid resource containing several
independent schema violations to be collapsed back to one diagnostic: that
would directly violate #450 for immutable ingress.

`PresentationIngressRejected` is therefore the shared aggregate boundary for
Draft and immutable Context resolution.  It transports an ordered, immutable
diagnostic sequence and cannot produce a render closure.  Existing
`ClosureError` remains the result only for a single collected diagnostic and
for terminal boundaries where a complete resource set cannot be known.

The CLI's existing diagnostics-array serializer projects this error without a
new command or renderer path.  Multiple entries retain resource provenance;
the one-entry legacy JSON shape remains unchanged.
