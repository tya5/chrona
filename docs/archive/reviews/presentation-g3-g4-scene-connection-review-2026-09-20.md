# G3/G4 Scene Connection Design Review

**Status:** Historical record of the former G3/G4 completion judgment. The integrated
audit in `g1-g4-integration-audit-2026-09-20.md` withdrew that judgment. Treat this
document only as historical context until the R01–R04 corrective design is complete.

| Boundary | Fixed contract | Prohibited recovery |
|---|---|---|
| View → annotation Scene | Project only explicit `object/id/facet/endpoint`; diagnose an omitted facet or missing Actual | Infer planned or select the first target |
| Box → leader | Use the first legal box from a finite candidate set. Exclude only its own anchor mark during box-candidate checks; keep other marks, required labels, and resolved boxes as collision objects. Use the nearest rectangle-edge port. | Manual coordinates, tails, waypoints, curves, or exclusions other than the anchor mark |
| Leader → routing | Treat all marks, required labels, and resolved boxes as obstacles. Allow only the first outgoing segment to touch the source-mark boundary. Stop at the Layout state limit. | Unbounded search, confusing meaning with dependencies, or making the entire source mark transparent |
| Annotation → lane | Exclude annotation boxes from lane occupancy. G3 resolves box collisions in stable annotation order. | A box-placement/lane-stacking cycle or adapter reinterpretation |
| Mark → lane Scene | Record View group/order, stable item order, and the lowest non-overlapping stack in Scene. | Adapter reordering or moving an item to another group |
| Lane → adapter | `row-aligned` retains `stackIndex` as metadata; `independent-lane-track` converts it to a vertical offset using Scene-derived pitch and track bounds. | Reinterpreting schedule, label occupancy, or stacks; implicitly breaking row correspondence |

## G4 surface boundary

`row-aligned` is the compatibility surface that preserves existing table/timeline row
correspondence and retains `stackIndex` as Scene metadata. Only
`independent-lane-track` creates a derived track per group and consumes pitch,
`trackPadding`, and `trackGap` determined by
`scene-mark-extent-plus-clearance`. This prevents visual omission of stacks and leaves
no room for an adapter to infer row height.

## Closing the cycle

`labels.anchorObstaclePolicy = exclude-own-anchor-from-box-collision` is a local rule
used only for box placement. `annotations.laneOccupancy = exclude-annotation-boxes`
defines the G4 occupancy boundary. G3 therefore treats only resolved boxes as
obstacles for later boxes, while G4 determines stacks from marks and required labels
only. Neither waits for unresolved output from the other, so the order is unique and
terminating.

## Fixture acceptance

The two projects in `presentation-g2-g4-design-v0.1.yaml` contain long Japanese text,
missing Actual, candidate overflow, unsupported anchors, stack overflow, and route
limits. Implementation tests additionally verify box-port tie breaking, route-state
limits, omitted-facet diagnostics, and lane-metadata invariance.

The former conclusion recorded that the authoring owners, Scene output, finite
procedures, diagnostics, and prohibited recoveries required for remaining G3/G4 work
were uniquely closed. Reproduction of R01–R04 shows that connection to public outputs
and evidence closure were not complete.

## Implementation verification

G3 connected explicit facet anchors, own-anchor exclusion during box candidate checks,
and leader routing with the full obstacle set to the SVG adapter. G4 preserves View
group order in Scene and derives independent-lane-track height and stack offsets.
`row-aligned` preserves the existing one-item-per-row behavior. The full regression
suite passed 164 tests with two existing DeprecationWarnings. That count alone is not
acceptance evidence for R01–R04.
