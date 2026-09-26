# Architecture Review — Progress Track Inset (#430)

**Decision:** design approved for implementation planning. **Reviewed design:** [#430 design](../../design/issue-430-progress-track-inset-design-2026-09-26.md).

| Boundary | Authority | Result |
| --- | --- | --- |
| Theme | Theme v0.11 role properties; v0.12 inheritance | One additive optional property (`progressInset`) plus an existing one (`markCornerRadius`) on `progress-fill`. The v0.11 schema was extended in place by earlier features. #478's role/property admission (the other session) must register both for `progress-fill`; noted for its rebase. |
| Layout | Specification 61, #397 | Geometry and radius are completed in `progress_fill_bounds`. There is one formula, and it reduces to today's at zero inset. |
| Scene / adapters | Specification 08 | A completed radius on an existing Rect primitive. No adapter policy. |
| Evidence | Example materializers | A new slide; the other 21 must stay byte-identical, which is literal criterion 3. |

**Risks:** the new slide adds a public materializer, which the corpus-coverage and reachability tools must accept; they are checked in conformance.
