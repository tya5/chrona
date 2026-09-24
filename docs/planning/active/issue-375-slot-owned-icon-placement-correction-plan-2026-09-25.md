# Design Correction Plan: Slot-owned icon placement (#375)

**Status:** Accepted.

## Trigger

I375-3 full-suite execution exposed three draft-render failures.  The I375-0
closure assigned an `IconPlacement` with no owner to `annotations` as a
fallback.  That assumption is invalid when no annotation slot exists and also
loses a group-header host's resolved table owner.  The failing targets are
plot labels, variance labels, and group-header labels.

## Questions to resolve

1. How does Layout resolve a host text placement's declared collision-domain
   source to one actual surface slot before a label visual is placed?
2. Which exact Layout slot owns annotation-box and annotation note-index
   visuals, without inferring from Scene purpose, coordinates, or ID parsing?
3. How will the completed placement boundary reject an unowned icon before
   Scene projection while preserving the no-geometry-inference rule?
4. Which focused regressions cover optional annotation-slot absence and each
   currently failing label-host class?

## Required outputs

* An English correction design and architecture-alignment review.
* An implementation plan that makes slot identity an explicit Layout fact for
  every icon placement.
* Focused Layout/Scene assertions and the previously failing draft-render
  cases, followed by the normal full release gate.

## Guardrails

* Do not restore a Scene-side fallback, parse identifier prefixes, or infer an
  owner from bounding-box containment.
* Do not make `annotations` required merely to support unrelated visuals.
* Do not alter View syntax, emitted visual geometry, or artifact bytes except
  where an explicit v0.2 `slotId` correction is required.
