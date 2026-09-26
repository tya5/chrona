# Architecture Review — Axis Template Correction (#432)

**Decision:** accept [the correction](../../design/issue-432-axis-name-table-template-validation-correction-2026-09-26.md)
as an amendment to the [#432 architecture review](issue-432-axis-name-table-architecture-review-2026-09-26.md).

The ISO week-year belongs to the natural interval and is already computed
by the temporal axis model. Supplying it as a closed formatting component
does not move temporal ownership into a resource or adapter. Rejecting
partial-month collisions prevents a table's alias declaration from hiding
an output-dependent ambiguity. The same validated table still drives trial
measurement and final Layout placement. No schema migration change or
additional layer connection is required.
