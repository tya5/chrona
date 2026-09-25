# Correction Review — Annotation Fallback Closure (#449 I449-4)

**Design:** `issue-449-visible-fit-failure-policy-design-2026-09-25.md`.
**Implementation plan:** `issue-449-visible-fit-failure-implementation-plan-2026-09-25.md`.
**Corrects:** the I449-4 acceptance review.

## Finding

The original I449-4 implementation completed ordinary plot labels, axis
labels, dependency relations, group headers, and dependency-network geometry,
but left two annotation placement paths able to reject a normal request:

- an aligned annotation box that escaped its slot or intersected an obstacle;
- an exhausted annotation rail or a leader route that exceeded the route
  quality limit.

This was an implementation omission, not a design ambiguity.  The #449 design
already requires every normal fit or placement failure to complete visible
Layout geometry and a typed warning; only a View-declared `suppress` may omit
the result.

## Correction

`project_annotation_box` and `place_annotation_rail` now retain deterministic
visible geometry when `visible-overflow` is selected.  The composition ladder
tries its declared non-suppress rungs normally, then completes its first rung
visibly if none fits.  A declared `suppress` remains the sole suppression
outcome.

Annotation leader routing now falls back in Layout to the direct endpoint
path when bounded routing or route-quality evaluation cannot complete.  Both
annotation-box and leader fallbacks join the existing typed `FitWarning`
closure before Scene projection.  Scene and renderers receive no new policy
branch.

## Boundary and architecture review

The correction preserves the intended responsibility split:

- Layout owns the finite candidate ladder, visible fallback, direct route, and
  warning identity.
- Scene projects the completed placements unchanged.
- Targets serialize the completed canvas and never crop or invent a fallback.

Anchor validity, unsupported annotation kinds, invalid metric resources, and
unknown references remain integrity errors rather than fit failures.

## Acceptance evidence

Focused annotation, label, network, Scene, and render tests cover the shared
paths.  The annotation unit test explicitly covers an oversized/colliding box
and an oversized rail under `visible-overflow`.  Diagnostic inventory,
primitive-delivery, and import-direction checks remain current.  Public
materializer and corpus evidence are rechecked in the I449-5 release gate.
