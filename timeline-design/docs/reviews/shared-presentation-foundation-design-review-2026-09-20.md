# Shared Presentation Foundation G0 / G2–G4 Design-Consistency Review

**Conclusion:** G0 is closed. G2–G4 were compared against
`31-presentation-g2-g4-design-gate.md`, each owning schema, and positive/negative
fixtures. Their design is closed to an implementation-ready level; implementation is
not complete.

## Confirmed consistency

| Boundary | Conclusion | Basis |
|---|---|---|
| Annotations | Generalizable | Combine existing View anchors/text, Scene Rect/Text/Path primitives, and Layout slots. |
| Prevention of exceptions | The mechanism reads no sample or preset name | ADR-0019 admission gate and owner separation in the wire fixture. |
| Time axis | Multiple slots can synchronize | A normalized scale derived from the View window and an explicit `scaleId` contract. |
| Semantic separation | Dependencies and leaders can reuse one router | Keep `sourceKind`, endpoints, roles, and accessibility separate. |
| Detail milestones | Not a second source of explanation text | The point list is a derived surface; text comes from View annotations. |
| Legacy | Not mixed with new functionality | Retain the Specification 29 legacy-adapter diagnostic. |

## Decisions

A callout is admitted as a target reference, measured text bounds, a finite candidate
set, and an optional orthogonal leader. Specialized tails, manual coordinates, manual
bends, arbitrary shapes, and unbounded search are rejected. This lets the same
implementation serve at least two uses among labels outside bars, work notes, and gate
explanations.

The decision not to render relation, group, or temporal annotation anchors in the
initial implementation is intentional. Existing concepts accepted by the schema are
held with an explicit diagnostic rather than ambiguously converted into object anchors.

## Fixture verification

`fixtures/validate_shared_presentation_foundation.py` validates the wire schema and
fixture and checks owner separation, week axes, annotation leader/routing, and the
Scene/Layout responsibility boundary. It validates design fixtures; it does not prove
SVG or placement behavior.

## Remaining implementation prerequisites

- G1 corrects unconsumed v0.2 settings and font/metrics problems.
- G2 implements schema fields in each authoring owner and adds the migration adapter
  and negative fixtures.
- G3/G4 admit only elements that successfully reuse G2 shared text, anchor, occupancy,
  and routing.

If implementation reveals an expression that cannot satisfy this contract, pause that
implementation and update the design first.

## Cross-check across G2–G4

| Boundary | Conclusion | Schema / fixture evidence |
|---|---|---|
| Label text and placement | Detail owns text; Layout owns finite candidates and overflow. The renderer has neither arbitrary expressions nor unbounded search. | `detail.labelRules`, `layout.labelPlacement`, candidate-overflow fixture |
| Facet paint | Resolve group override, default, then normalized global role. Do not mix it with a group-background map. | `theme.facetPaints`, group-override fixture |
| Axis slot | `timeline-axis` shares the timeline scale; diagnose a different scale. | `layout.slots`, Specification 31 `E_PRESENTATION_SCALE_MISMATCH` |
| Annotation | Initially render only typed View object references; accept no manual coordinates or waypoints. | Faceted anchor in `view-v0.1`, missing-Actual and unsupported-anchor fixtures |
| Leader routing | Orthogonal leaders use Layout's bounded route limit and share a router while remaining a distinct role from semantic dependencies. | `layout.routing.limit`, route-limit fixture |
| Lane stack | Follow View group/order and select the lowest stack from mark and required-label occupancy. | `layout.lanes`, stack-overflow fixture |

## Diagnostics and prohibited recovery

| Diagnostic | Owner | Prohibited recovery |
|---|---|---|
| `E_PRESENTATION_LABEL_UNPLACEABLE` | Layout | Clip a required label or search unbounded candidates |
| `E_PRESENTATION_SCALE_MISMATCH` | Layout | Use a separate window/scale per slot |
| `E_PRESENTATION_ANCHOR_MISSING` | View projection | Substitute planned when Actual is missing |
| `E_PRESENTATION_ANCHOR_UNSUPPORTED` | View / adapter | Ambiguously convert relation, group, or temporal to object |
| `E_PRESENTATION_STACK_OVERFLOW` | Layout | Move to another group, implicitly shrink, or hide |
| `E_PRESENTATION_ROUTE_LIMIT` | Layout | Search without bound after the limit |

`validate_presentation_g2_g4_design.py` checks two projects without fixed IDs, long
Japanese text, missing Actual, and five negative diagnostics. It validates design
input; later implementation tests prove placement and SVG rendering behavior.
