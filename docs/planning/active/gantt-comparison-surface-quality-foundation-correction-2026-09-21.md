# Gantt Comparison Surface Quality — Foundation Completion Correction

**Status:** Design correction complete.
**Amends:** ADR-0031, the #58 implementation plan, and the design review.

## Trigger

Before starting I58-3, inspection of `v05_builder` found that Scene still reads font metrics, chooses plot-label coordinates, and calls `route_orthogonal`. The I58-1 data types introduced by #62 are useful but do not satisfy the ADR-0031 ownership boundary.

## Decision

Treat I58-1 as partially delivered, not complete. Finish the foundation before enabling any I58-3 policy:

1. Layout receives the semantic label and relation requests together with completed mark, table, axis, annotation, and timeline geometry.
2. Layout measures label text, selects candidates, invokes routing, scores routes, and returns accepted or explicitly suppressed placements.
3. Scene consumes those placements to emit primitives. It has no font-metric or routing import and does not choose a label or route coordinate.
4. Characterization evidence proves the migrated default placements preserve the prior bytes until I58-3 activates the new policy forms.

The public label-overflow and relation-quality behavior remains I58-3. This correction changes implementation sequencing only; it introduces neither a compatibility fallback nor an example-specific branch.

## Acceptance gate

I58-1 is complete only when all of the following are true:

- `v05_builder` does not import font metrics or `route_orthogonal`.
- A typed placement result contains all text and relation geometry used by Scene.
- Scene has no call that measures label text, derives plot-label coordinates, or routes a relation.
- Characterization tests and public materializer byte checks pass without a user-visible policy change.

Only after that gate is merged may I58-3 add the schema policies, diagnostics, neutral fixtures, HALCYON declarations, and regenerated outputs as its atomic vertical slice.
