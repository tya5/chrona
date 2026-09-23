# Issue 308 Progress Fill Implementation Plan

## Scope

Implement only Specification 61.  #310 inside labels and #314 declared
colour scales are accepted dependencies, not implementation inputs to reopen.

## Slices

1. **View and semantic closure.** Add the closed `progressFill.source`
   vocabulary to the current View contract and add the `progressFill` semantic
   binding/Theme role.  Reject an invalid source before render.
2. **Typed Layout submark.** Carry selected actual/planned progress with the
   review item.  Extend the completed Layout placement closure with optional
   progress-fill Rect placements derived from host bounds.  Test zero, half,
   full, missing source, missing host, and fractional bounds.
3. **Projection and public evidence.** Project completed progress placements
   through Scene with no fraction/geometry calculation.  Add a HALCYON public
   View/theme example, regenerate its SVG, and prove source metadata and paint.
4. **Release gate.** Run focused schema/Layout/Scene/materializer checks, full
   pytest, conformance, all public materializers and generated SVG diff, then
   wheel and isolated installed-wheel smoke.

## Acceptance

* Progress has one declared source and never changes schedule facts.
* Layout, not Scene or SVG, owns submark bounds and zero-width omission.
* The submark has a closed semantic/Theme role and completed adapter paint.
* Existing label/scale behavior and public Context materializability remain
  intact.
