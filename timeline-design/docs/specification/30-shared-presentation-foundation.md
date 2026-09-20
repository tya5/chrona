# Shared Presentation Foundation: Admission Boundary and Generalized Annotations

**Status:** D1/D2 design complete; runtime correction not implemented.
**Basis:** ADR-0019. This specification adds an admission boundary without replacing
Specifications 06/07/08/27/28/29.

## 1. Goals and non-goals

Compose tables, labels near bars, gate-explanation bands, and team lanes from shared
mechanisms over one plan. Pixel reproduction of image concepts is not completion.
Arbitrary-shape editors, general constraint languages, free scripting, and proliferating
dedicated panels are out of scope.

## 2. Ownership and shared mechanisms

| Concern | Authority | Prohibited duplication |
|---|---|---|
| Schedule, Actual, variance | Project / Schedule / Actual / View Projection | Recalculate dates or variance in Layout |
| Visible objects, groups, annotation text/references | View; semantic annotations in Project | Select independent targets in Layout |
| Facts→semantic roles | Style | Infer state from color |
| Visual decoration | Theme | Separate annotation-only Theme system |
| Wording and allowed formatting | Detail | Renderer-specific template language |
| Regions, dimensions, constraints, search | Layout plus normalized existing Scene profile | Pixel coordinates in View |
| Text/symbol measurement input | Explicit fixed Render Context assets per family×weight | Substitute regular for bold |
| Shapes, positions, connections, provenance | Scene | Replacement in SVG adapters |

Shared internal elements are not a new persistent copy of semantic data: a View-derived
time scale shared by regions; marks derived from span/point and planned/Actual facets;
text regions measured once with wrapping, bounds, and baseline; anchor resolution from
stable ID/facet/endpoint to projected ports; shared placement boundaries, obstacles,
and candidates; and a router shared by dependencies, leaders, and explanatory arrows
while preserving each source kind, meaning, visibility, endpoint, and accessibility.

The sole derived assembly DTO is `ResolvedPresentationInput`. It carries
`semanticFacet`, `visualRole`, `slotId`, `projectionInstanceId`, measurement requests,
resolved Layout/Theme/Detail/Context, and resolved surface-slot, row, and lane-track
bounds. Derive `projectionInstanceId` deterministically from
`slotId + sourceRef + semanticFacet + primitivePurpose`; Scene IDs use it as a prefix.
Visual roles never overwrite facets. Multiple slots and colocated facet/role instances
remain distinct. DTOs, measurements, and Scene are derived and never persisted in View
or Layout.

The DTO includes a closed `SurfaceContentInput`, normalized exactly once by the
application boundary: ordered column IDs and cell display strings; typed selected
relations; typed visible annotations; ordered note text; resolved legend entries plus
coverage text; and declared summary panels. A normalized summary panel is the closed
tuple `(panelId, headingText, metrics)`, where every ordered metric is
`(metricId, formattedText)`. `formattedText` already contains its localized label,
separator, availability wording, and value. Scene retains `panelId` / `metricId` for
identity and emits `headingText` / `formattedText` verbatim; it does not reconstruct
display wording from IDs. Scene construction consumes these values but no Project,
View, Schedule, or authoring-settings resource. Optional absent families are empty;
missing required normalized values yield
`E_PRESENTATION_INPUT_INCOMPLETE`. SVG adapters never see this DTO.

The application entry path may accept `SurfaceContentInput` as a derived parameter,
but the selected SVG serializer receives only its completed `SceneSurface`. The
minimal entry path normalizes selected `Scene.relations` into the DTO once; the review
entry path normalizes selected relations, visible annotations, and declared summary
panels before Scene construction. Legacy entry paths without resolved settings remain
explicitly isolated and are not evidence for I3 completion.

After measuring content, pass temporary `intrinsicBlocks` / `intrinsicTracks` to the
solver; never persist them or replace unmeasured values with fixed pixels. Equal input
closure, font assets, locale, and candidate order must reproduce equal intrinsic values.

The fixed font-metrics table is resolved by relative resource path plus content
identity. Font outlines and a host font-family lookup are not part of the measurement
closure. Axis labels, Symbol shapes, marker shapes, mark opacity, and planned/Actual
dimensions are completed Scene properties; the serializer does not recover them from
authoring settings or replace them with adapter defaults.

## 3. Generalized callouts

A callout is not a special component. Project an existing annotation into a target
reference, measured text region, finite placement constraints, Theme decoration, and an
optional leader. The same parts also serve bar/end labels, table cells, legends, gate
explanations, and date/milestone notes. Minimum acceptance covers a note attached to an
Actual finish and a note pointing from another region to a planned gate through the same
implementation. An explanation band is a composition of ordinary regions and selected
View annotations, not another fact source.

Initial scope covers spans/points of already selected objects. Text is existing View
annotation text or formatted allowed facts; do not infer delay causes. Preserve
relation/group/temporal anchor concepts but diagnose unsupported input instead of
substituting an object. Accept only rectangular text and optional orthogonal leaders.
Comic tails, multi-target leaders, embedded arbitrary images, and manual waypoints are
out of scope. Leader omission when text touches a target is explicit policy.

Resolve planned/Actual facets explicitly; never move a missing Actual anchor to planned.
Normalize View `finish` to Schedule `end` through a meaning table. Do not connect to
unselected targets unless the View contract says so. Project and View-local annotations
share placement but retain provenance/edit ownership. Include stable slot ID in Scene
identity; diagnose ambiguous projection instances. Annotation changes never alter
Schedule, Actual, or dependencies.

The finite order is: validate closure/references/capabilities/owners; build scale and
base mark bounds/ports; measure all required text; test finite candidates in stable
source and declared candidate order; route with resolved text obstacles and source-kind
policy; validate required content, boundaries, endpoints, accessibility, and provenance;
then emit Scene. Never move base marks in time, loop placement without bound, shrink or
hide text, detach anchors, or invent regions. Failure diagnoses placement or routing;
the algorithm need not solve every geometrically feasible diagram. Expand legacy
preferred sides into explicit candidates, use only one old/new search policy, and
version candidate generation, limits, and tie breaks.

## 4. Application to candidate features

- A week axis implements the existing axis contract with closed calendar, locale, and density rules.
- D nearby labels are the first shared text/anchor/placement consumer.
- B explanation bands compose regions, scale, selected points, and annotations; resolve View-versus-Detail authority first.
- C lanes implement Specification 06 stable stacking with text occupancy; row-aligned and stacked lanes are Layout policies, not renderers.
- Team color resolves Theme from stable group reference plus semantic role; renderers never branch on IDs.

## 5. Design integration gate

Reuse View annotations/placement (06), Style roles and Theme decoration (07/29), Scene
Rect/Text/Path (08), Layout slots/regions (27), and Detail point-explanation intent (28).
Before implementation, close facet/endpoint normalization, legacy migration,
unsupported-anchor diagnostics, group×facet paint precedence, projection-instance
identity, shared scales and content dimensions, a single View/Detail source of truth,
legacy isolation, and migration of direct-SVG measurement/placement/routing into Scene.
Accepted annotation commands do not prove renderability. Close wire schemas, fixtures,
compatibility, diagnostics, and acceptance evidence first.

## 6. v0.1 wire contract and future owners

`shared-presentation-foundation-v0.1.schema.json` is design-validation wire data that G1
distributes to existing owners. It is neither persistent authoring data nor renderer
input.

| Wire section | Sole v0.2 owner / destination |
|---|---|
| `scale` | Layout `axis` and `scale` |
| `marks.comparisonModes` | Layout `bars.comparisonMode` |
| `marks.pointKinds` | Theme planned/Actual/baseline symbols |
| `facetColors` | Theme `facetPaints[groupId][facet]` |
| `labels` | Detail text plus Layout candidates/overflow |
| `annotations` | View text/anchor, Layout candidates, Theme box/leader |
| `lanes`, `routing` | Layout |

Keep `groupPaints` for group backgrounds. Facet paint resolution is group+facet,
default facet, then global facet paint within complete resolved Theme. Never mix
backgrounds with facets or branch in a renderer.

## 7. Normative display and placement

Date-only weeks are ISO-8601 Monday-start and labeled `YYYY-Www`. Locale affects wording,
not week start. List unique levels coarse-to-fine (quarter/month/week/day) with equal
`bandHeights` length. Diagnose unsupported, duplicate, or out-of-order levels.
`tickUnit/tickStep` set grid cadence only. Slots sharing `scaleId` use the same View
window/padding and normalized date position, although origins and widths may differ.
Diagnose conflicting windows. Spans are `[start,end)` and points use `at`; only
human-readable finish display may use `end - 1 day`.

Initial `comparisonMode` values are `stacked`, `overlaid`, and
`baseline-and-actual`. Missing Actual applies only `missingActual` policy. Emit point
Actual only with observed `at`, and span Actual only with both observed endpoints.
Never infer a missing endpoint. Finish variance is calendar-day Actual finish minus
planned end; preserve negative/zero/positive roles and `showZero`. Always consume Theme
Actual height, point shape/size, and variance-marker width.

Label rules specify text source, facet/endpoint, candidate-side order, requiredness, and
overflow. Sources are title, closed date formatter, comparison delta, or existing
annotation text—never arbitrary expressions. Evaluate at most sixteen candidates in
stable source/rule/candidate order; `inside` requires measured text to fit.

View annotations preserve typed anchor, purpose, and text. Callout/note use a box and
policy-controlled optional leader; highlight is decoration with no required text or
leader; explanatory-arrow uses exactly two existing anchors and retains a distinct
`sourceKind` from dependencies. Endpoint normalization is: span `start`/`finish` map to
the matching observed facet endpoint; point `at` requires an explicit facet; `body`
uses the mark/symbol center. Unsupported non-object anchors diagnose
`E_PRESENTATION_ANCHOR_UNSUPPORTED`; absent facet/endpoint/instance never falls back.

View group/order fixes lane order. Place each item at the lowest non-overlapping stack
using resolved mark plus required-label occupancy and stable object-ID ties. Overflow
never moves groups. `row-aligned` keeps one item per row and stack index as metadata.
Only `independent-lane-track` converts stack index to Y. With
`scene-mark-extent-plus-clearance`, `pitch = markExtent + routing.clearance` and
`trackHeight = 2*trackPadding + markExtent + maxStackIndex*pitch`; use `trackGap`
between lanes. Treat a colocated table as another slot.

Dependencies, leaders, and explanatory arrows may share a finite orthogonal visibility
grid but retain source-kind stroke layer, endpoints, meaning, and accessibility.
Required marks/text/boxes/arrowheads are obstacles; paths are not. Routing consumes
`gridOffset`, `clearance`, `portOffset`, `bendPenalty`, `limit`, and stable tie breaks.

### 7.5 D2 geometry and purpose projection

The Scene Builder alone performs this finite sequence: solve each public surface's
title/timeline/axis/row/lane-track bounds; construct date scale, axis bands, ticks, and
surface-local date-to-X; create facet-preserving marks and shape ports; measure one
`TextLayout {bounds, baseline, lines, family, weight, assetIdentity}`; resolve lanes
from mark plus required-text occupancy; create purpose-specific annotation primitives
and finite routes; then finalize IDs, `sourceKind`, bounds, z-order, manifest, and
diagnostics. Later stages never reinterpret earlier ones.

The final manifest is the closed derived shape in Specification 08 §3.4. In particular,
each public surface owns a scale record with its Date domain and usable output range,
origin, and logical-units-per-day ratio. The same record is attached to the completed
`SceneSurface`; this is the only scale evidence available to an adapter. The manifest
also records the settings version, logical viewport, ordered selected IDs, declared
font-asset identities, and the five normalized optional-family counts. It contains no
Project/View payload and introduces no new authority.

Before text measurement, the Scene Builder evaluates the resolved Detail heading and
optional subtitle templates against the closed permitted-value map. It emits
`title-text` and optional `subtitle-text` with their final wording, bounds, baseline,
and `TextLayout`. The SVG adapter receives neither the templates nor their source facts.
For group surfaces, resolved Theme paint serialization includes opacity as well as color;
opacity is not an adapter default or a geometry exception.

The application boundary supplies that permitted-value map in
`SurfaceContentInput.templateValues`; its closed keys are `title`, `windowStart`,
`windowLastVisible`, `selectedCount`, `unmatchedCount`, and `missingCount`. Scene never
parses formatted coverage text or consults a projection to reconstruct a missing value.

The implementation DTO is closed by primitive kind: Rect=`bounds`; Text=`text` plus
one TextLayout; Symbol=`shape` plus bounds; Path=`points` plus optional
`fromPortId`/`toPortId` only for non-connector ticks. A connector or leader without both
port IDs, a Path with fewer than two points, or any payload/kind mismatch is
`E_PRESENTATION_PRIMITIVE_INVALID`. Path bounds are derived from the ordered points.
Adapters map primitive kind/purpose plus `visualRole` to paint tokens only and never
repair geometry or payloads. Foreground Text mapping is distinct from the containing
axis/table surface mapping: axis labels use foreground text paint with level typography,
and table-column labels use foreground text paint with table-header typography. A
single role-to-color lookup that makes required foreground equal its background is
invalid.

Axis identity includes `(scaleId, level, naturalInterval.index, slotId)`, mark identity
includes `(projectionInstanceId, facet, markRole)`, and Text identity includes
`(projectionInstanceId, textRole)`. Adapters never recalculate band height, X/Y,
baseline, tracks, or routes. Review/minimal serialize only their completed selected
surface, never settings margins/day width/row height or projected order.

Purpose contracts are: callout/note = Text + Rect + optional Path leader with one object;
highlight = Rect/Symbol only with one object; explanatory-arrow = Path + arrowhead with
two objects. Never convert a leader to dependency, demand text for highlight, infer an
anchor, or collapse a two-anchor arrow.

Ports come from span/point boundaries and are identified with
`projectionInstanceId`. Only box-candidate checks may exclude that annotation's anchor
mark. Routing restores all marks, required labels, and resolved annotation boxes; only
the first outward source-port segment may touch its boundary. Never exclude a colocated
different object, slot, or facet. Point occupancy remains a point, not a one-day span.
`row-aligned` uses stacks as metadata; independent lanes use
`trackPadding + stackIndex*pitch` as their sole Y offset. Insufficient bounds,
`maxStack`, or required-label failure yields `E_PRESENTATION_STACK_OVERFLOW`.

The finite route tie-break uses coordinates, direction, bend count, and stable ID.
Exceeding state `limit` yields `E_PRESENTATION_ROUTE_LIMIT`; exhaustive no-path yields
`E_CONNECTOR_UNROUTABLE`. Do not merge them.

## 8. Migration and duplicate declaration

Move v0.1 View annotations unchanged as logical anchor/text; migrate
`layoutIntent.itemStacking: stable` one-way to `layout.lanes.stacking`; move Scene
Profile routing/collision to v0.2 Layout. Reject old/new duplicate annotation candidates,
scale, routing, or lane policies with `E_PRESENTATION_DUPLICATE_AUTHORITY`.

Detail `milestones` remains a derived surface listing View-selected point IDs. An
explanation band has no Detail-owned coordinates/text; it projects View annotations into
the annotations slot. Milestone and annotation references to one point remain separate
primitives. Retain the Specification 29 legacy adapter until G1 completes, always emit
`E_PRESENTATION_LEGACY_ADAPTER`, never mix it with v0.2 paths, and add no new features.

## 9. Diagnostics and design fixtures

| Diagnostic | Condition | Prohibited recovery |
|---|---|---|
| `E_PRESENTATION_AXIS_INVALID` | Invalid levels/heights/order/week | Implicit month axis |
| `E_PRESENTATION_SCALE_MISMATCH` | Shared slots disagree | Silently choose one |
| `E_PRESENTATION_ANCHOR_UNSUPPORTED` | Anchor outside initial scope | Convert to object |
| `E_PRESENTATION_ANCHOR_MISSING` | Missing facet/endpoint/instance | Substitute planned |
| `E_PRESENTATION_LABEL_UNPLACEABLE` | Required text fits no candidate | Shrink, hide, detach |
| `E_PRESENTATION_STACK_OVERFLOW` | Stack or lane bounds exceeded | Move group or overlap |
| `E_PRESENTATION_DUPLICATE_AUTHORITY` | Old/new policy coexist | Merge or implicit priority |
| `E_PRESENTATION_INPUT_INCOMPLETE` | Required normalized surface content is absent | Read Project/View/settings in an adapter |
| `E_PRESENTATION_PRIMITIVE_INVALID` | Primitive kind and payload disagree | Infer or repair payload in an adapter |
| `E_CONNECTOR_UNROUTABLE` | Finite search has no route | Free-form path |

The positive fixture validates owners, week axes, comparison marks, labels, object
annotations, stable stacking, and source-kind routing; the negative fixture covers
ordering and non-ISO week start. Validators check design-fixture consistency, not
runtime behavior. Implementation adds positive/negative cases for every diagnostic,
two projects, long Japanese text, missing Actual, and reproducibility.
