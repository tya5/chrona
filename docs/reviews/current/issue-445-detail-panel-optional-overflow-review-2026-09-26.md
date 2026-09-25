# Architecture Review — Optional Detail-Panel Overflow Correction (#445)

**Correction under review:** `issue-445-detail-panel-optional-overflow-correction-2026-09-26.md`  
**Status:** Accepted.

The correction is required: an adapter has no completed Text clipping contract,
so preserving an oversized `clip-optional` Text primitive would contradict both
the declared disposition and the projection-only boundary.  Layout-owned
suppression is already the model's explicit representation for an optional
semantic placement.  Carrying a typed warning through Scene retains observable
provenance without converting a renderer into a policy owner.

The following guardrails apply:

1. suppression is permitted only after Layout measured an entry against an
   optional `clip-optional` panel slot; required slots remain rejected by the
   existing Layout Profile validation;
2. the Scene builder skips a suppressed side-content placement generically,
   rather than encoding a #445-specific adapter condition;
3. `ellipsize-with-source` and `visible-overflow` remain distinct completed
   Layout outcomes; and
4. the new warning is included in the diagnostic inventory and direct Scene
   serialization coverage.

This correction preserves the #449 finite fallback taxonomy and introduces no
new public syntax, compatibility reader, or general Scene containment policy.
