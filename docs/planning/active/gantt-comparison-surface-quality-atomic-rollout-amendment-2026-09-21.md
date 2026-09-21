# Gantt Comparison Surface Quality — Atomic Rollout Amendment

**Status:** Design correction complete.
**Amends:** Specification 50 §6 and the #58 implementation plan.

## Trigger

I58-2 table feasibility would correctly reject current HALCYON table slots: their Layout policy is `overflow: diagnose`, while their selected date columns do not fit at the declared viewports. Merging that behavior before the declarative resource migration would make a currently materializable example fail solely because delivery order was wrong.

## Decision

Keep the structural placement refactor independently mergeable, but deliver every user-visible feasibility policy as an **atomic vertical slice**:

1. implementation of the generic Layout/Scene/schema policy;
2. neutral fixture and diagnostic tests;
3. all affected declared example resource changes; and
4. public materializer regeneration and acceptance evidence.

No merge may activate a stricter interpretation of an existing public resource unless every affected declared context either remains feasible under its current declarations or is adapted in the same merge.

## Revised I58 order

- **I58-1:** placement foundation refactor only; no output policy change.
- **I58-2:** table allocation implementation, View/Layout policy normalization if needed, neutral tests, HALCYON table declarations and regenerated evidence in one atomic slice.
- **I58-3:** labels and relation quality implementation, policy normalization, neutral tests, HALCYON label/relation declarations and regenerated evidence in one atomic slice.
- **I58-4:** group header and legend implementation plus only the selected HALCYON resource declarations and regenerated evidence.
- **I58-5:** final automated and visual release gate.

## Invariants

- Existing generated examples never become temporarily unmaterializable on main.
- No compatibility fallback is added to Scene or SVG.
- A resource change remains declarative and contains no example identifier branch.
- A slice that discovers another affected context returns to design/impact inventory before merging.

## Review

The amendment preserves the generic solution: atomicity controls rollout only and does not change ownership. Layout remains the sole geometry authority; examples merely select the public policies.
