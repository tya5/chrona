# Issue #46 HALCYON authoring implementation plan

## Preconditions

The HALCYON resource-authoring specification and its architecture review are approved. Implementation preserves the existing Project / View / Layout Profile / Theme / Scene boundaries.

## Phases

1. Extend View schema and normalization for typed table facets and formatters; add focused unit coverage.
2. Add normalized temporal presentation: axis settings, as-of marker settings, calendar closure shading, and structured labels compatibility.
3. Add typed summary figures and deterministic numbered annotations.
4. Add semantic Theme bindings and author the HALCYON-1 resources only through public contracts.
5. Materialize every declared HALCYON context through the public CLI, save SVG evidence, and add regression tests. Full `pytest` is delegated to the user-designated AI.
6. Publish implementation review with command evidence, close the issue only after all declared contexts reproduce.

## Acceptance criteria

- No HALCYON-specific renderer branch or manually drawn final SVG.
- Planned, actual, and finish-delta table values are resource-addressable and formatted by contract.
- Target slides use rows/groups, axis, marker, shading, annotations, and summaries through their proper owners.
- Existing authoring inputs retain compatibility.
- All manifest contexts materialize deterministically.

## Publication

Each completed phase is committed through GitHub before the next phase begins.