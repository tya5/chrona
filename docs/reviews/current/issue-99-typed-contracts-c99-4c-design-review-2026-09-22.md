# Issue 99 C99-4C Closure Consumer Completion Review

**Decision:** Approved for implementation planning.

The residual generic helper is a real boundary leak, not merely an internal
convenience: a future caller can request arbitrary kind strings and recover a
frozen document without declaring its dependency.  Named accessors plus an
explicit read ledger preserve the same runtime behavior while making resource
dependencies reviewable.  The proposed source checks are intentionally scoped
to closure consumers, not all domain mappings, so they do not conflate
serialized-resource ownership with scheduler/layout semantic facts.
