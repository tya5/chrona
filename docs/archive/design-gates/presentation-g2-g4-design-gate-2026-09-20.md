# Shared Presentation Foundation G2–G4 Design Gate

> Historical design-gate record. Normative ownership now resides in Specifications 08, 27, 29, and 30. Specification ID 31 remains retired and reserved.


**Status:** D1–D3 design is complete. Earlier G1–G4 completion judgments are
withdrawn. Implementation starts with a Scene Builder that satisfies the D3 acceptance
table and design validators.

## 1. Single authoring owner

The Scene Builder derives one `ResolvedPresentationInput` from the owners below and
sets `projectionInstanceId = slotId + sourceRef + semanticFacet + primitivePurpose`.
A visual role is decoration selected by Theme; it neither renames nor substitutes a
semantic facet. A renderer serializes only a completed Scene and MUST NOT recompute
slot selection, font measurement, anchors, lanes, or routes.

| Value | Owner | Renderer input | Prohibited behavior |
|---|---|---|---|
| Label text source and template | Detail | Resolved Detail | Arbitrary expressions or renderer wording |
| Label candidates, maximum candidates, and overflow | Layout | Resolved Layout | Object-ID branches or unbounded search |
| Annotation text and typed anchor | View | Resolved View | Pixel coordinates or manual waypoints |
| Box/leader paint | Theme | Resolved Theme | Annotation-specific Theme family |
| Facet paint | Theme | Resolved Theme | Mixing a map with group background |
| Lane group/stack/maximum | Layout | Resolved Layout | Moving groups in the renderer |
| Route grid/clearance/limit | Layout | Resolved Layout | Confusing `sourceKind` semantics |

## 2. G2: labels, facet paint, and axis slots

`detail.labelRules[]` has `{id, source, facet, endpoint, required}` and
`layout.labelPlacement` has `{candidateSides, maxCandidates, overflow}`. The only
sources are `title`, a closed date formatter, `comparison-delta`, and
`annotation-text`. At most sixteen candidate sides are evaluated in stable-source-ID,
rule, then candidate order. `inside` is legal only when measured text bounds fit inside
mark bounds. An unplaceable required label is
`E_PRESENTATION_LABEL_UNPLACEABLE`; an optional one follows the explicit `overflow`
policy.

`theme.facetPaints` is
`{default: {planned, actual, baseline, variance}, groups: {groupId: {...}}}`.
Resolution is `groups[groupId][facet]`, then `default[facet]`, then the existing global
role. The final global role becomes a concrete paint during resolved-Theme
normalization; the renderer does not reimplement this order.

An axis slot uses the `timeline-axis` source in `layout.slots` and requires the same
`scaleId` as its timeline slot. Sharing a different window or scale is rejected with
`E_PRESENTATION_SCALE_MISMATCH`.

## 3. G3: annotations and leaders

The initial target is only a View object anchor. Consistent with existing typed View
references, an anchor is `{kind: "object", id, facet, endpoint}`; facets are
`planned`/`actual`, and endpoints are `start`/`finish`/`at`/`body`. Missing Actual MUST
NOT fall back to planned. Relation, group, and temporal anchors remain valid input but
produce `E_PRESENTATION_ANCHOR_UNSUPPORTED` in the initial implementation. A missing
target facet, endpoint, or projection instance produces
`E_PRESENTATION_ANCHOR_MISSING`.

Annotation purposes are `callout`, `note`, `highlight`, and `explanatory-arrow`.
Callouts and notes allow a rectangular box and optional orthogonal leader; a highlight
allows only a box; an explanatory arrow allows only a path with two object anchors. A
leader has at most one source and target and allows no manual coordinates, curves,
tails, or waypoints. Candidates use the same finite ordering as labels, and routing
stops at the Layout routing limit.

`theme.annotation` provides three concrete paints: `{boxFill, boxStroke, leader}`.
Box dimensions, candidate sides, and leader-search limits belong to Layout, not Theme.
No purpose-specific Theme family is created.

For each annotation, Scene emits
`{annotationId, objectId, facet, endpoint, boxBounds, leader}`. `boxBounds` is the
first legal candidate of the shared label placer. The box-side port is the midpoint of
the rectangle edge closest to the anchor (`above`, `below`, `end`, `start` breaks a
tie). Box-candidate collision checks exclude **only the annotation's own anchor mark**
from the obstacle set; other marks, required labels, and earlier annotation boxes
remain. A leader is an orthogonal path from the anchor port to the box port and treats
all marks, required labels, and resolved annotation boxes as obstacles. Only the first
outgoing source-port segment may touch the source-mark boundary. Annotation boxes are
not part of G4 lane occupancy, preventing a placement/stacking cycle; box-to-box
collisions are resolved solely in stable annotation order. `routing.limit` bounds the
number of states expanded on the visibility grid; excess is
`E_PRESENTATION_ROUTE_LIMIT`. A `highlight` emits no leader, and an
`explanatory-arrow` emits only when both explicit object anchors are present. A legacy
View annotation without a facet remains schema-valid for storage compatibility, but
G3 Scene projection returns `E_PRESENTATION_ANCHOR_MISSING` and does not infer
`planned`.

## 4. G4: stable lane stacking

Lane order is View group/order; insertion order within a lane is
`(mark.start or mark.at, stable object ID)`. An item's occupancy is the union of its
mark and required-label bounds, and it takes the lowest non-overlapping stack index.
Exceeding `maxStack` or failing to place a required label yields
`E_PRESENTATION_STACK_OVERFLOW`. No item is moved to another group, implicitly shrunk,
or hidden.

Scene adds `laneGroupId` and `stackIndex` to every projected mark. View group/order
sets `laneGroupId` order, and each group assigns in `(start or at, stable object ID)`
order. The `row-aligned` surface retains one item per row and keeps `stackIndex` as
Scene metadata. Only `independent-lane-track`, which visualizes multiple stacks,
consumes it: Scene derives pitch from resolved comparison-mark block extent and routing
clearance, then emits a group track of
`2*trackPadding + markExtent + maxStackIndex*pitch`. The adapter merely converts
stack index, pitch, and track bounds to vertical offsets; it MUST NOT reselect,
reorder, move items between groups, or implicitly preserve row correspondence.

## 5. Design-completion checks

Before G2–G4 implementation, complete all of the following.

1. Place the fields above in existing View/Theme/Detail/Layout v0.2 schemas; keep wire
   schemas as mappings only.
2. Add valid/invalid fixtures for every field: more than sixteen candidates, missing
   Actual anchor, group facet override, stack overflow, independent lane track, and
   route limit.
3. Verify inputs, owners, and prohibited recoveries for `E_PRESENTATION_*`
   diagnostics in review.
4. Confirm reproducibility using two projects without sample-specific IDs/names and
   with long Japanese text and missing Actual data.

Until this work is complete, do not implement G2 label/facet paint, G3 annotations, or
G4 lanes in Python.

## 6. D2 algorithm acceptance contract

Specification 30 §7.5 is the sole owner of projection order, the purpose table,
port/obstacle exceptions, the lane formula, and route-failure classification. The
G2–G4 fields here define only their inputs. Implementation MUST NOT report completion
until acceptance tests demonstrate drawing and collision checks with the same
`TextLayout`, non-span handling for points, purpose-specific primitives,
`projectionInstanceId` distinction of separate marks at the same coordinates, and the
distinction between `E_PRESENTATION_ROUTE_LIMIT` and `E_CONNECTOR_UNROUTABLE`.

## 7. D3 schema and evidence closure

The wire-schema routing requires `gridOffset`, `clearance`, `portOffset`,
`bendPenalty`, and `limit`. `row-aligned` retains `stackIndex` as Scene metadata and
is not limited to stack zero. Positive/negative fixtures and the validator for
`shared-presentation-foundation` verify these requirements and permit no missing
Specification 30 §7.5 input. During implementation, acceptance traceability maps the
required cases in `g1-g4-integration-remediation-2026-09-20.md` to specification
sections, schema paths, implementation symbols, and tests.

`presentation-scene-input-v0.1.yaml` is not an authoring schema. It is a derived input
fixture for the slots, rows, and lane-track bounds passed to ResolvedPresentationInput.
Its validator verifies the closed input set that lets an adapter receive only a
completed Scene.

