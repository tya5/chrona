# Design — One Layout Placement Model and Shared Obstacles (#466)

**Status:** the shared-obstacle prerequisite is design-complete. Candidate
schema, nearest-free search and tail treatment below are an architectural
direction, not approved for product implementation until a later design
completion and whole-architecture review publish their exact contracts.

**Plan:** [#466 design plan](../planning/active/issue-466-general-placement-design-plan-2026-09-26.md).
**Related:** [#467 lane plan](../planning/active/issue-467-lane-packing-design-plan-2026-09-26.md),
[#413 ladder correction](issue-413-annotation-placement-ladder-correction-2026-09-25.md),
[Specification 33](../specification/33-intent-oriented-layout.md).

## Boundary and use cases

A note beside a dependency route must not cover it merely because rail and
side placement received different obstacle lists. A plot balloon may search
free space near its anchor and, if none exists, take a declared rail fallback.
The same obstacle facts must also be usable by packed-item labels in #467.

View declares *intent* (ordered candidates, annotation purpose and anchor);
Layout normalizes candidate rules, measures text, searches, routes, and emits
completed box, text, connector and decision placements. Theme provides
appearance and a finite tail/balloon treatment. Scene only projects these
placements; SVG/PNG/typeset adapters only serialize. Semantic dependency
routes remain Project-derived, not annotation connectors.

## Typed surface obstacle inventory

One `SurfaceObstacleIndex` is created per surface composition. It is a typed,
deterministically ordered set of `Obstacle` records: stable placement ID,
class, slot/region ID, exact rectangle or stroke-segment geometry, effective
clearance and optional host identity. Classes include mark (planned, actual,
baseline and glyph bounds), text, gate/port, as-of or declared grid rule,
dependency route, leader route, annotation box and label visual. A line is
tested as stroked segments, not as the enclosing route rectangle. Group/row
backgrounds are not obstacles merely because they paint behind content.

The index is created once and monotonically receives completed geometry.
Queries use one API, accepting region, required obstacle classes and explicit
exemptions. An inside label may exempt only its named host mark; a route may
touch its source/destination port but not pass through an unrelated mark.
Annotation text and its own box are a declared containment pair; the box is
still an obstacle to later requests. There is no global exemption for the
current row, object, purpose or paint order.

To avoid circular placement, Layout closes geometry in finite phases:

1. slots, rows, marks, ports and rule lines;
2. plot labels, including later #467 item names/deltas and the lane packing
   decisions those labels constrain;
3. semantic dependency paths and their required route labels, routed around
   the already accepted labels;
4. annotations in stable View order, adding each accepted box, text and
   connector before evaluating the next annotation;
5. optional decorative visuals that do not alter earlier geometry.

This order lets #467's lane decision account for measured labels before row
geometry is final. A dependency route must then avoid those accepted labels;
labels cannot be required to avoid routes that do not yet exist. If a new
route family needs the reverse order, its owner must declare a reserved
measured obstacle before placement or add a separately reviewed bounded
phase; no hidden circular retry is allowed. The index is one evolving
closure, not several purpose-specific obstacle copies. Any new family must
declare its phase and class before it can participate.

`SurfaceObstacleIndex` is renderer-neutral. Layout's existing
`LabelObstacle` and `LabelRect` are adapters to the one query, not alternate
authorities. Route quality (bend/detour limits) remains separately checked.
The index and candidate decisions carry stable IDs into structural tests;
they do not become persisted Project facts.

## Candidate contract to complete in a later design slice

Each normalized candidate has exactly four fields:

| Field | Closed values / meaning |
| --- | --- |
| `region` | named slot, plot, content, or intersection; resolved to a finite Layout rectangle before search |
| `search` | `row-aligned`, `adjacent` with side, or `nearest-free`; each has an explicit finite enumeration bound |
| `obstacles` | named classes from the one index; semantic marks/text/routes/boxes are required for plot search; grid/as-of barriers are selected explicitly |
| `connector` | `none`, orthogonal `leader`, or outline `tail`, with endpoint and route limit |

View/normalization binds an ordered candidate list. Current rungs expand to
data, without changing their outward spelling: `rail` is annotation-slot +
row-aligned + leader; `above`, `below`, `start`, `end` are side regions +
adjacent search + the purpose's existing leader choice; `suppress` remains a
terminal outcome rather than a candidate. The expansion is explicit and
checked by byte characterization before new search kinds are enabled. The
purpose of a callout/note/highlight/explanatory arrow never changes candidate
selection; purpose only chooses semantic treatment and connector capability.

Candidates are tried in declared order. Within one candidate, deterministic
search order is anchor distance, block distance, inline distance, then
block/inline coordinate and candidate index; all coordinates are normalized
to Layout precision. `nearest-free` walks a finite grid derived from measured
box size and declared step/limit, never local machine font or time. It does
not cross the as-of line when that barrier class is declared. A candidate
decision records candidate ID, search count, fit/visible-fallback/suppressed
status and the obstacle IDs that caused a failed preferred position. The
chosen candidate is emitted in one structured diagnostic when fallback
occurs; ordinary first-choice fit needs no warning.

If no candidate fits, the existing #449 policy still applies: an explicit
`suppress` rung can suppress; otherwise Layout completes the first
candidate visibly with a warning. It never refuses solely because the slide
is dense, never leaves an unrecorded overlap, and never silently changes
purpose. Leader routing uses the same index and bounded route search;
visible direct-route fallback is recorded when route quality cannot fit.

## Tail and balloon

`tail` is a connector from the selected box outline toward the resolved
anchor port. Layout owns attachment and shape geometry, including collision
and required clearance. Theme binds one finite `annotation-container`
treatment with fill/stroke/radius and optional tail style; the fallback
Theme treatment remains a plain rectangle and leader. A tail is not a
semantic dependency and must not alter its source/target semantics. Scene
projects a renderer-neutral path or polygon plus text/box primitives; SVG
and PNG produce equivalent shape, with source and asset identity preserved.
Image-backed annotation containers (#465) are a separate paint extension.

## Migration, diagnostics and proof

The shared obstacle stage may intentionally move an annotation or leader
that previously covered a mark/label/dependency. Record all resulting
Scene/SVG differences as corrections, not unexplained churn. Candidate
normalization alone must then be byte-identical against that new baseline.
No public resource spelling changes in the obstacle-only stage. The later
candidate grammar and Theme treatment require versioned View/Theme schema
updates, typed normalization, examples and migration notes; do not overload
an old rung string with hidden search parameters.

The dependency-line fixture proves stage 1. Stage 2 proves byte parity for
legacy rungs. Stage 3 proves all three HALCYON notes inside plot without
mark/label/route overlap or as-of crossing, a crowded plot-to-rail fallback,
bounded deterministic search counts and decisions. Stage 4 proves tail
and balloon in SVG and PNG, and exact plain-Theme parity. #466 closes only
when all seven literal acceptance rows and CI/release evidence are met.
