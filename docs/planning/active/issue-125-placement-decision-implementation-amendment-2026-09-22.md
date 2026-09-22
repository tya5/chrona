# Issue 125 Placement-decision Implementation Amendment

## Preconditions

This amendment implements the placement-decision correction.  It follows the
merged View v0.4 design and PR #207's extension-boundary correction.  No
generic presentation package or relation fallback syntax is introduced.

## Slices

1. **Typed intent and schema closure.**  Update View v0.4 to expose only
   validated label and annotation/callout ladders, with terminal-suppression
   invariants.  Carry row/item intent through projection and normalize the
   selected annotation occurrence without adding coordinates to View.
2. **Completed Layout decision closure.**  Add immutable placement-decision
   evidence to `SurfacePlacement`.  Implement label/callout candidate search,
   deterministic wrapping, and explicit placed/suppressed/diagnosed results.
   Associate callout geometry, text, and leader with one decision.
3. **Projection-only regression gate.**  Add schema, normalization, Layout,
   and Scene tests proving that Scene receives completed decisions but cannot
   measure, choose candidates, or route.  Run focused tests, full `pytest`,
   public materializer checks, and generated SVG characterization together at
   the final gate.

## Acceptance criteria

* Invalid ladders fail schema validation before materialization.
* A label or anchored callout uses the first feasible declared rung and has
  one inspectable `PlacementDecision` with the same provenance.
* `suppress` emits an explicit optional placement outcome; a non-suppressing
  exhausted ladder raises the established Layout diagnostic.
* Wrapping is deterministic and only enabled by its View intent.
* Existing public materializers retain their bytes unless a fixture explicitly
  exercises the new View v0.4 feature.
