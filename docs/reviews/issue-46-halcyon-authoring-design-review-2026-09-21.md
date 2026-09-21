# Issue #46 HALCYON authoring design review

## Scope reviewed

The HALCYON-1 target resources are reviewed against the current Project / View / Layout Profile / Theme / Scene architecture and the row-mapping (#41) and slide-vocabulary (#42) contracts.

## Findings and decisions

| Concern | Decision | Owner |
| --- | --- | --- |
| Slide-specific renderer behavior | Prohibited. Encode composition in resources and reusable View/Profile contracts. | View/Layout |
| Planned / actual / delta table values | Add typed View table facets and formatters. | View |
| Temporal display choices | View selects axis, as-of marker, and calendar shading; Project remains the source of facts. | View / Project |
| Dossier figures | Use typed summary metrics, labels, and formatters. | Summary profile |
| Notes and callouts | Preserve semantic annotations and add deterministic numbered presentation. | Annotation presentation |
| Visual language | Use semantic Theme roles; no legacy Settings/Theme restoration. | Theme |

## Boundary verification

- Project owns calendar, review-item intervals, actual dates, metadata, annotation targets, and locale-neutral facts.
- View owns row membership, grouping, column sources, presentation mode, labels, and temporal display choices.
- Layout Profile owns frame and region geometry.
- Theme owns resolved colors, strokes, typography, and mark sizing tokens.
- Scene is materialized output only.

## Compatibility and accessibility review

- Existing boolean `visibility.labels` remains accepted and normalizes to the structured contract.
- Existing Views omit new fields and render unchanged.
- Missing actual data remains explicit text rather than an ambiguous empty timeline mark.
- Marker, closure shading, table values, legend, headers, and annotations use semantic roles so contrast can be governed centrally.

## Materialization review

The declared HALCYON contexts are the acceptance surface. The implementation must materialize each with the public CLI, save SVG evidence, and avoid asserting a manually reconstructed slide.

## Approval

Approved for implementation. No conflict with the deleted legacy Settings/Theme contract was found.