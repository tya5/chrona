# Architecture Review — Member Labels Stay in Their Own Row (#488)

**Decision:** approved. **Reviewed:** [#488 design](../../design/issue-488-member-label-row-band-design-2026-09-27.md).

| Boundary | Result |
| --- | --- |
| Layout | The region is an existing `LabelRequest.bounds` input. No new search, and no second placement path. |
| View / Theme | Unchanged. The declared ladder and chip padding keep their meaning. |
| Evidence | Slides with plot labels move or suppress labels that used to leave their rows. Each change is attributed in the slice review. |
