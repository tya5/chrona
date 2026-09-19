# M23 Reference-quality review surface plan

**Priority update:** User explicitly deferred outside-Gantt components. Observation
tables and milestone digests are NOT in the current implementation scope. Gantt
geometry/customization correction is reviewed separately in
`../reviews/gantt-reference-correction.md`; M23 is not claimed complete by that work.

The Controller Z reference demonstrates presentation surfaces that M21 named but the
adapter did not yet implement: owner descriptions, a semantic legend, a source-labelled
observation table, and a milestone digest.  M23 closes this implementation gap without
adding scheduling semantics.

| Step | Deliverable | Gate |
|---|---|---|
| D23 | `28-review-detail-profile.md`, Layout source integration and contract review | Completed by this document. |
| I23 | Generic parser/validator, deterministic slot allocation and SVG primitives | No title/preset branches; source metadata tests. |
| A23 | Controller Z detail resource and visual comparison against the supplied reference | raster review, conformance, unit tests, and output reproducibility. |

The Detail Profile is owned by Presentation. Project remains the owner of plan and
relations; Actual Set remains the owner of observations that have been reconciled as
Actual. Supplier commentary remains read-only presentation evidence with provenance.
