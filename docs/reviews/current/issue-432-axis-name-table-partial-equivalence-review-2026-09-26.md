# Architecture Review — Month-Specific Equivalence (#432)

**Decision:** accept [the correction](../../design/issue-432-axis-name-table-partial-equivalence-correction-2026-09-26.md)
as an amendment to the [#432 review](issue-432-axis-name-table-architecture-review-2026-09-26.md).

The resource validator, not a View or adapter, owns the complete coincidence
inventory. Layout knows the selected form and natural bucket month, so its
warning is exact and cannot drift from measured text. A month-scoped record
does not affect interval identity, calendar computation, font metrics,
fitting, Scene serialization or Render Context defaults. The correction
preserves the published layer chain and strengthens the literal acceptance
gate: even a one-month collision is never silent.
