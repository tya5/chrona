# Gantt Comparison Table Feasibility — I58-2 Implementation Plan

**Status:** Design correction and implementation plan.  I58-2 begins only after
I58-1 merge `7ee38f3`.

## Correction

The pre-Foundation `place_table_columns` implementation is not I58-2 completion:
its `ellipsize-with-source` path proportionally shrinks column bounds but retains
unellipsized text.  That violates Specification 50 §3.1.  It is retained as the
current baseline only until this atomic replacement is reviewed and merged.

## Contract

Layout measures every normalized header and cell.  It calculates a deterministic
per-column minimum, including a declared inter-column gap.  `diagnose` emits
`E_LAYOUT_TABLE_OVERFLOW` before Scene if their sum exceeds the table slot.
`ellipsize-with-source` allocates deterministic non-overlapping widths, emits a
measured ellipsized `TextPlacement`, and preserves full content and source
provenance.  Scene projects those placements without truncation logic.

## Atomic implementation unit

1. Replace proportional shrink allocation with measured minima and deterministic
   remaining-space allocation in Layout; add placement provenance for ellipsized text.
2. Normalize the selected table overflow declaration once at ingress, and reject
   unsupported forms before Layout.
3. Add neutral overflow and ellipsize fixtures plus A58-02 placement assertions.
4. Inventory every HALCYON context; adapt every infeasible table declaration in the
   same PR, with no identifier-specific runtime branch.
5. Regenerate affected expected SVG only through the public materializer after full
   tests and PNG review.  No partial policy/resource merge is permitted.

## Acceptance and publication

Focused Layout/Scene/schema tests, full pytest, all public materializer checks, and
reviewed PNG evidence must pass.  Publish this design correction first; publish the
implementation as a separate PR only after that design PR is merged.
