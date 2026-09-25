# Architecture Review — Downstream Detail-Panel Allocation Correction (#445)

**Correction under review:** `issue-445-detail-panel-downstream-allocation-correction-2026-09-26.md`  
**Status:** Accepted for corrective implementation.

The correction addresses a real ownership breach: a late-completed Layout
block changed a parent flow's physical extent without completing the later
Layout slot that the same flow had positioned from its provisional extent.
Leaving the overlap for Scene or #446 would turn a quality observer into an
allowlist for known broken geometry.

The constrained successor rule is accepted because it uses only completed
Layout source/geometry facts, retains the profile's existing downstream gap,
and runs before annotation composition.  It does not add a general
post-hoc collision solver, a View coordinate, an adapter fallback, or a new
Scene contract.  The implementation must verify both no-growth byte stability
and the Controller-Z annotations case, then amend the #445 implementation
plan and regenerate all public evidence before #446 work resumes.
