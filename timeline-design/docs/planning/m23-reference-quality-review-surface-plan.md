# M23 Reference-quality review surface plan

**Priority update:** Gantt geometry/customization correction was completed separately
and did not claim M23. M23 is now authorized as the next product-quality milestone and
completes the previously deferred outside-Gantt review surfaces without reopening
scheduling semantics.

The Controller Z reference demonstrates presentation surfaces that M21 named but the
adapter did not yet implement: owner descriptions, a semantic legend, a source-labelled
observation table, and a milestone digest.  M23 closes this implementation gap without
adding scheduling semantics.

| Step | Deliverable | Gate |
|---|---|---|
| D23 | Profile schema/fixture, completed `28-review-detail-profile.md`, Layout/Scene input contract, and design review | Complete; `m23-review-detail-design-review-2026-09-20.md` authorizes I23 after publication. |
| I23 | Generic parser/validator, deterministic slot allocation and SVG primitives | Complete; no title/preset branches, with semantic, source metadata, overflow, and compatibility tests. |
| A23 | Controller Z detail resource and visual comparison against the supplied reference | Complete; zero raster overflow, exact SVG reproduction, full conformance, and visual acceptance review. |

The Detail Profile is owned by Presentation. Project remains the owner of plan and
relations; Actual Set remains the owner of observations that have been reconciled as
Actual. Supplier commentary remains read-only presentation evidence with provenance.

Every phase is published serially. Any implementation-discovered unowned choice pauses
I23, updates the owning specification/schema/fixture and design review, validates and
publishes that addendum, then resumes implementation.
