# Gantt Comparison Label and Relation Quality — I58-3 Acceptance Review

**Status:** Accepted for publication after I58-2 merge `c4639ec`.

## Architectural consistency

The public View normalizer is the only ingress for label and relation overflow
policy.  Layout Profile owns the route-quality limits.  Layout measures finite
label candidates, records an explicit suppression when declared, and accepts or
suppresses completed routes before the Scene boundary.  Scene emits only accepted
placements; it does not measure text, choose a label side, or route a relation.
This preserves the Project → View → Layout Profile → Layout → Scene →
SVG/PNG ownership in ADR-0031 and Specification 50.

## Acceptance evidence

- Neutral placement tests cover finite label candidates, explicit suppression,
  bend/detour limits, and Scene projection of accepted placements only.
- `finishDelta` is composed either into the declared label or as its standalone
  variance placement, never both.
- All materializable Controller-Z, ASTER, and HALCYON contexts declare or retain
  an explicit policy; HALCYON Views and Layout Profiles are adapted atomically.
- Regenerated SVGs were rasterized at their declared viewports and visually
  reviewed: no clipping or unintended text overlap was found; deliberately
  suppressed routes are absent rather than degraded.
- Full test suite: `251 passed` (seven pre-existing jsonschema deprecation
  warnings). Public materializer byte checks pass after regeneration.

## Scope boundary

This slice adds no new View content syntax beyond overflow declarations and no
new routing algorithm.  Group headers and legend policy remain I58-4 work.
