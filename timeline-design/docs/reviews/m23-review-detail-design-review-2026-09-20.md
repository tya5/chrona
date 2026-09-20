# M23 Review Detail design review — 2026-09-20

## Decision

D23 is complete and authorizes I23. The original design named the four review-detail
surfaces but left three runtime boundaries ambiguous. This review closes them before
implementation: the profile schema, the View/Project validation boundary, and the
resolved Layout-to-Scene binding.

The v0.2 path has one legend authority: `presentation-settings/v0.2.detail.legend`.
The Review Detail Profile therefore carries only group descriptions, the ordered
milestone selection, and source-labelled observations. It cannot override the legend.

## Closed contracts

- `review-detail-profile-v0.1.schema.yaml` owns the authoring shape. Duplicate group,
  column, or row IDs and non-rectangular observation cells diagnose deterministically.
- Group IDs must occur in the selected Review Projection. Milestone IDs must resolve to
  selected Point objects. Profile order is preserved.
- Every observation row has non-empty provenance. Observation text remains literal,
  read-only presentation evidence and never becomes Actual or scheduler input.
- Layout sources are `group-details`, `observations`, and `milestones`. A declared panel
  binds exactly one slot. Missing required content, duplicate source slots, unknown
  references, and required overflow diagnose; optional absence produces no primitive.
- Scene owns all panel geometry and source metadata. SVG adapters only serialize
  completed primitives. The same resolved closure produces identical bytes.

## Reuse and authority review

No title, preset ID, sample name, or Controller Z branch is authorized. Wording and
content remain in YAML resources. Project owns object titles and scheduled dates; View
owns selection and group order; Detail owns presentation-only descriptions and
observations; Layout owns rectangles; Scene owns measured geometry.

## Design gate evidence

The schema and positive/negative fixture validator pass together with full existing
conformance. I23 may start only after this design checkpoint is published.
