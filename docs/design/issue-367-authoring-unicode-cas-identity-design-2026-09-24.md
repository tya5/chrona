# Issue 367: authoring Unicode CAS identity design

The authoring use case and its persistence adapter share one revision boundary.
`chrona.operational.resources.content_identity` is therefore the sole identity
codec for both `baseRevision` validation and compare-and-set writing.  A
command-local serializer is removed rather than aligned by convention.

This is a persistence-boundary correction only: Draft remains mutable source,
Context remains immutable evidence, and no Store reference is synthesized.
Japanese regression coverage proves a current workspace can update itself;
stale revisions remain rejected.
