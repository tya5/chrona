# #321 Schema Annotation Applicator Correction Architecture Review

**Authority:** Specification 56 and the applicator-correction plan.

**Result:** Accepted for implementation.

The correction preserves the annotation model's distinction between an
author-facing local constraint and pure schema reuse.  Reaching all `allOf`
branches is necessary to make the existing normative promise true; treating
every `$ref` wrapper as author-facing would instead duplicate prose for reuse
plumbing.  Branch-level conditional annotation remains the right granularity,
provided structural `allOf` wrappers cannot prevent traversal from reaching it.

The lint stays at the source-schema quality boundary.  It does not modify
resource validation, normalization, placement, Scene projection, or renderer
serialization.  The design is therefore consistent with the repository's
inward dependency direction and completed-placement architecture.
