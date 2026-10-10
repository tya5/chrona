# 50. Constraint-driven Gantt Surface Quality

**Status:** Proposed — Issue #58 design
**Depends on:** Specifications 37, 44, 49 and ADR-0031.
**Owns:** the generic feasibility, placement, diagnostics and acceptance contract for a completed Gantt review surface.

## 1. Ownership

| Layer | Owns | Must not own |
| --- | --- | --- |
| Project / Actual | dates, dependencies, calendar, observation facts | visual geometry |
| View | selection, grouping, columns, label/relation intent | coordinates or pixel thresholds |
| Theme | typography and declared numeric metrics | content choices or collision decisions |
| Layout | all measurement, constraints, placement, routing and feasibility | Project semantics or SVG serialization |
| Scene | placement-to-primitive projection and z-order | font measurement or geometric search |
| SVG/PNG | serialization and visual evidence | policy inference |

## 2. Structural refactor

Before any functional change, replace Scene-owned geometry helpers with the following immutable internal values:

- `SurfaceLayoutRequest`: canonical table cells, Review rows/members, axis facts, label requests, relation endpoints, decoration requests, resolved slots, Theme metrics and FontMetrics identity.
- `SurfacePlacement`: table columns/cells, rows/tracks/marks, axis text slots, label placements, group header placements, relation placements, decoration placements and ordered diagnostics.

Diagnostic provenance (#918) is an immutable, non-rendered sidecar captured
from explicit typed source facts at the producer. Layout retains Project
object pointers and known titles for object-backed warnings, including
suppressed placements; Scene projects these facts without parsing identifiers.
Exact primitive identities may join Scene findings to explicit subject facts.
View, axis, slot, group and relation sources are not assumed to be Project
objects. Multi-owner findings retain ordered subjects. The sidecar is not a
serialized Scene/schema field: existing per-placement diagnostic strings,
warning identities/multiplicity, geometry, paint and SVG/PNG bytes remain
unchanged. Spec 66 owns the message and transport projection.
- `TextPlacement`: source id, content, measured bounds, typography role, overflow result (`fit`, `ellipsized`, or `suppressed`).
- `RelationPlacement`: source/target ports, path, quality measurements, or explicit suppression.

Layout returns only completed placements. Scene accepts `SurfacePlacement` and is prohibited from importing the router or FontMetrics.

## 3. Feasibility contract

### 3.1 Table

For every table column, Layout measures the header and all selected normalized cell strings. A `visible-overflow` table slot retains measured unbroken bounds and completes visible natural geometry even when it escapes the allocated slot; Layout expands the completed canvas where needed. Layout MUST NOT uniformly shrink columns below those bounds.

For `ellipsize-with-source`, Layout allocates deterministic widths, produces ellipsized `TextPlacement` values, and retains full source text/provenance. Every text a composer ellipsizes also produces a `W_LAYOUT_TEXT_ELLIPSIZED` fit warning with the natural and available inline sizes (the legend, #497); a committed Scene with an ellipsized `legend:*` text and no such diagnostic fails `tools/check_legend_truncation.py`. `visible-overflow` produces `W_LAYOUT_VISIBLE_OVERFLOW` with required/available facts. Non-intersection is required only for an author-selected policy that requests it; a visible fallback may deliberately overlap rather than remove content.

### 3.2 Labels and delta

View label intent becomes:

```yaml
visibility:
  labels:
    placement: plot | table | none
    content: [title, finishDelta]
    side: auto | start | end
    overflow: suppress | visible-overflow
```

`plot` creates ordered candidates at the eligible mark sides and ranks them against required table text, axis text, marks, accepted labels, required annotations, and viewport bounds. `auto` tries start then end in deterministic order. If no candidate fits, `visible-overflow` completes the first ranked candidate with a warning; explicit suppression remains an author choice. A plot member name with an own mark is a narrower exception: its visible fallback must also satisfy the completed mark-association rule below, or fail with `E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE`; other label families retain the general fallback.

Generated lanes use Spec 38's plot-name contract: `title` is always selected,
`finishDelta` is selected by default but may be omitted, and an authored side
and fallback take precedence over `auto`'s end/start/stagger default. The
terminal outcome for a name that cannot fit is source-keyed suppression and
counting, never a new lane or visible overflow. The general visible-overflow
policy remains available to automatic and explicit rows.

Before any row, mark, table cell or note placement, Layout applies the
measured table-timeline content requirement to the complete Layout Profile
allocation. A known row-density requirement grows its table/timeline host and
moves later normal-flow slots when that profile can grow. `visible-overflow`
remains the fallback for a valid profile whose host is fixed/capped or for a
different placement collision; it is not permission to leave notes over a
known growable table. The completed canvas still contains every emitted
primitive.

For data-owned lane rows, the requirement includes the full measured internal
mark-subtrack extent of every fixed lane, not a one-band estimate. Layout may
use a seed allocation to obtain the inline scale, close each lane's mark
facets and subtracks once, then feed their block requirement to the final
profile allocation. The same completed subtrack plan is reused for row and
mark placement; the final inline frame MUST match the seed frame. This
preflight neither reassigns lane membership nor searches for a block-height
fixed point. A capped host may retain a measured overflow diagnostic, but a
growable host MUST contain the final lane rows and marks.

For a `fill` lane surface, preflight and final placement share one normalized
member-label intent and Theme-measured box. Preflight uses the completed scale
and selected mark/subtrack obstacles; inline-feasible end/start intervals
determine concurrent finite stagger levels and each row's minimum before
surplus distribution; relevant mark-obstacle intervals also contribute to
those levels. The minimum also includes a finite conservative envelope of one
measured block level plus placement clearance per selected lane name above
completed mark subtracks, because interval concurrency can undercount
cross-class obstructions. This requirement may grow the timeline host
when profile constraints permit. A short seed row is not grounds for
suppression.

For `fill` lanes, the finite preferred/contact search tests row edges and
current axis-aligned obstacles expanded by label bounds and clearance. For a
mark-associated member name, candidate block displacement is limited to the
preferred position and contact positions within one measured stagger step in
either direction: at most its measured label height plus declared gap, never a
second step. Select exactly one legal position. Search declared sides in order,
then absolute block displacement, smaller block coordinate and stable identity.
The final candidate must be in its own lane row and satisfy the mark-association
bound below. `pack` lanes and non-lane candidate-search domains are unchanged.

The completed Text bounds of every emitted plot member name with its own mark
MUST stay within the member-name reach (default two em, below) as a
two-dimensional nearest-perimeter gap of that exact
mark on either side, measured from the requested host. An item's own marks are
its planned (or baseline/snapshot) mark and its actual mark, when each is
drawn; an absence indicator (`missing-actual`) is not an own mark. When no
candidate on the declared ladder is legal and `end` is declared, a final rung
places the name after the right edge of the item's rightmost own mark, never
inside it, bounded by the reach from that edge and within reach of at least
one own mark; a visible-overflow fallback on `end` is measured from the same
edge. Only a name placed by the final rung or this fallback names the own mark
nearest its Text as `hostPlacementId` (the requested host on a tie). A name that
has a legal candidate on the ladder keeps its position and host. Layout rejects a farther candidate before trying the
next declared side. Default `auto` tries end then start; authored side/fallback
order remains authoritative. A suppressible request with no legal candidate
records its source-keyed suppression and aggregate count. After legal
candidates are exhausted, a declared `visible-overflow` request may emit the
first declared near-mark candidate despite a collision or viewport escape,
with the ordinary overflow warning; it cannot waive the association bound.
A required request with no valid near-mark candidate fails with
`E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE`; it never emits detached text. The
Scene acceptance check pairs each emitted member label to its own completed
mark through `hostPlacementId`, additionally checking lane/member identity
when present, never by visual order or nearest distance. No member-label
leader, route, endpoint exemption, or lane leader facet is emitted (#554).

A Layout Profile may declare the member-name policy in
`reviewSurface.memberNames`, an optional object with two optional members:

- `maxEndGapEm` (a number from 0 to 100, default `2`) sets the member-name
  reach to `maxEndGapEm` times the label font size. That one value bounds both
  the end-side gap and the nearest-perimeter association gap above, and the
  final-rung gap from the last own mark; `0` leaves no end placement.
- `search` (`side-band` or `full-band`) selects the block-position search.
  `full-band` runs the finite preferred/contact search across the row band,
  limited to one measured stagger step only for lane rows; `side-band` keeps
  the side-neighbourhood search. When `search` is omitted the default applies:
  `full-band` for a lane row under `rowDistribution: fill`, otherwise
  `side-band`. A declared value applies to every mark-associated member name,
  independently of row distribution.

Omitting `memberNames` (or a member) gives exactly the defaults stated here, so
existing profiles are unchanged. The object is added to the current Layout
Profile version in place (Spec 56 §3.2). A derived Layout Profile declares its
own `reviewSurface` and therefore its own `memberNames`; it does not inherit
the base profile's.

Each suppressed name has a typed `SurfacePlacement` fact with lane/member, final
row extent, remaining capacity and reason `capacity` or `obstruction`, validated
against its suppressed text placement and aggregate count. “Cannot grow” means
`fill` leaves no unallocated timeline block after headers and other row minima.
Capacity additionally requires allocator evidence naming the short required
timeline source. A final-row inline-bound, obstacle, or association miss is
obstruction, not capacity; Layout does not search hypothetical row heights.
An earlier example's zero-suppression output is characterization, not a
project-specific exception to the later #554 association rule. The
owner-approved adjacent/start/count outcome supersedes #504's historical
example stop gate for association failures. Report changed counts as evidence
and tune presentation through declared project resources, never Project data
edits made only to pass a render check.
Scene schema and aggregate diagnostics do not change except the #554 member
leader lane-facet retirement stated above.

The temporal scale's usable range reserves the maximum left and right extents
of selected point facets relative to their date anchors, including resolved
symbol, icon, rotation and stroke geometry. No selected point means no inset.
Its Date-only domain remains the View window; axes, calendar shading, marks
and routes use the same completed inset scale in lane preflight and final
composition. Layout diagnoses a non-positive usable range as
`E_LAYOUT_MARK_OVERFLOW` rather than letting an adapter clip the point.

**Explicit-window visibility closure (#1292).** Before point-inset measurement
or lane-footprint preflight, Layout derives one immutable visibility result per
instance and source facet from the projection's explicit-window provenance.
The same result drives automatic, lane and folded final composition; it does
not alter data-only lane membership. Disjoint spans and out-of-window points
are omitted, not mapped beyond the plot. Point insets include only admitted
facets and retain their existing complete symbol/icon/stroke geometry.

Intersecting spans retain original dates alongside the visible interval.
Progress is computed over the original span, then intersected with the visible
host; applying its fraction to an already shortened host is forbidden. Delta
facts remain original. Summary and missing-Actual geometry use the same
closure, not separate date-coordinate fallbacks.

Only original temporal endpoints that remain visible provide dependency ports:
span starts are in `[start, end)`, span exclusive ends in `(start, end]`, and
points in `[start, end)`. A window cut does not invent a temporal endpoint at
its edge. A relation lacking a required visible endpoint is suppressed with
`W_LAYOUT_RELATION_SUPPRESSED` and typed outside-window cause/source facts;
raw relation-anchor fallback is forbidden. Surviving route paint must remain
inside the completed plot.

Layout aggregates clipped or omitted object-backed facets into one
`W_LAYOUT_OUTSIDE_WINDOW` per surface, with deterministic deduplicated object
subjects and source refs (Spec 66); per-facet reasons remain typed internal
evidence. Unchanged contained facets and derived-window paths retain existing
Scene output and produce no outside-window warning. Neither Scene nor an
adapter chooses visibility, remeasures geometry, or changes the viewport to
accommodate omitted geometry.

The timeline as-of label is a constrained exception to generic
visible-overflow behavior. Layout measures its text and any declared chip
footprint, then tries the plot top margin beside the as-of rule followed by
finite rule-hosted chip positions within the plot. Every candidate must fit the timeline
slot and avoid all axis bands and axis text, data marks, accepted required
labels/annotations, and the as-of rule except for its explicitly identified
host attachment. No axis-side seam rung or overflow candidate is permitted.
Layout records the selected candidate and obstacle decision as completed
placement evidence, and later annotation routing treats its footprint as an
obstacle.

If no candidate is legal, Layout retains the as-of rule and records a
source-keyed `W_LAYOUT_LABEL_SUPPRESSED` disposition for the label. The
suppressed text is non-drawable: Scene MUST NOT emit it, and a serialized
Scene with a primitive named by that diagnostic is invalid public evidence.
This no-fit outcome does not claim that a declared visible-label acceptance
criterion was met; any profile promising a visible as-of label must have a
legal plot-side candidate. Ordinary label requests retain their declared
visible-overflow fallback. Scene and adapters do not retry, move, clip, or
repair the as-of label.

For suppressed plot member labels, Layout MUST also count completed
`memberLabel` text placements with `overflow: suppressed` once per surface.
No accepted start- or end-side member-name candidate may exceed the
two-dimensional own-mark association bound above. When no end candidate fits,
Layout tries the next declared rung; suppressible exhaustion records
suppression and the aggregate count.
When positive, the count is an `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=<surface-id>;count=<positive-integer>`
inspection diagnostic and an `info` CLI diagnostic. Its value MUST equal the
number of corresponding per-placement `W_LAYOUT_LABEL_SUPPRESSED` facts.
Scene projects the completed fact; adapters neither recount nor draw a marker.

`finishDelta` has exactly one text representation per item. When selected in `labels.content`, no second standalone variance text is emitted. Its semantic role remains derived from the signed value.

### 3.3 Relations

View relation intent becomes `none` or an object with `mode: semantic` and `overflow: suppress | visible-overflow`. Layout Profile adds `relationRouting.maxBends` and `relationRouting.maxDetourRatio` numeric geometry policy.

Layout routes between completed ports through deterministic orthogonal candidates. A route is acceptable when it stays in the timeline, avoids required obstacles, has at most `maxBends`, and its Manhattan length is at most `maxDetourRatio × directDistance`. Eligible candidates use the ranking below. With `visible-overflow`, no acceptable route completes as the deterministic direct path plus `W_LAYOUT_ROUTE_FALLBACK`; explicit suppression creates `W_LAYOUT_RELATION_SUPPRESSED`.

**Candidate search (#1109 R5).** One bounded sparse
visibility search supplies alternatives for each endpoint pair, rather than
post-filtering only a single length-plus-bend-penalty winner. Obstacle-offset
corners and endpoint projections seed the finite graph; exact inventory
queries determine clear edges. Constrained labels retain distinct canonical
prefix histories: a cheaper different path cannot erase an alternative before
path-dependent final validation. Cyclic prefixes are rejected. The deterministic expansion limit
is shared across a pair's candidate enumeration. Rehearsals and final Layout
use the same search and completed-route validation.

`relationRouting.entry` is an optional Layout Profile policy: `any` has no entry preference; absent or `side-when-free` prefers a horizontal span-start entry when the source is to its left (mirrored for span end). The full-radius corridor is offered first and a blocked corridor may use the head-plus-stroke minimum defined below. All horizontal stub pairs are tried across source exits before the other pairs (#1072). Every candidate retains normal bounds, mark/text/label, terminal and quality checks; remaining candidates stay eligible. Point targets and `at` endpoints are unchanged by `side-when-free` (#1030).

`relationRouting.entry: side` also offers horizontal point-target stubs at the left vertex for `start`/`at` (right for `end`). When ordinary selection does not side-enter a different-row target, Layout tries row-gap back-routes from each legal source egress: complete the source corridor and its own terminal reserve, reach the target row edge on the source side, cross to the entry tip, then enter the target horizontally. Each candidate must clear primary marks and other obstacles, avoid self-overlap, and satisfy the unchanged `maxBends` and `maxDetourRatio` against the shortest path retaining both corridors. Common node-clearance/entry/bend/length ranking still applies. A final non-side entry emits `I_LAYOUT_RELATION_ENTRY_FALLBACK:<scene relation id>;reason=<code>` (`same-row`, `entry-stub-blocked`, `degenerate`, `bends-or-detour`, `blocked:<class>=<placement ids>`, `node-approach-conflict` or `forward-entry-failed`).

Relation terminals are Theme `marker` tokens resolved by Layout (`relation_terminals.marker_geometry`) into completed outlines. `triangle` is a filled closed triangle; `open-triangle` is the same three-edge outline stroked, not filled; `chevron` is an open V with no closing edge (#1042). `stealth` is a filled notched triangle (notch 0.7 of the length from the tip); `rounded-triangle` a filled triangle with corners rounded to about 0.12 of the head width; `dot` a filled circle (a separate name from `circle` so a Theme can declare a smaller default); `half` a filled half arrowhead with one barb on the left of the line direction; `double-chevron` two stroked chevrons, one behind the other (#1044). Each takes `headLength`, `headWidth` and `attachmentOffset`. A round terminal (`circle`, `open-circle`, `dot`) is centred on the endpoint's semantic position (the start or end edge at the mark's vertical centre, a point mark's centre or tip) and the line touches its edge: Layout moves the first (source) or last (target) route point by the radius along its leg and sets the marker's reference so the circle lies behind the source's first point and ahead of the target's last point; a declared `attachmentOffset` is superseded for these shapes, and a leg shorter than the radius limits the shift to half the leg. Triangular heads keep their tip at the port. `none` draws no terminal (#1105): `marker_geometry` resolves it to no marker, the line starts or ends exactly at the endpoint with no setback and no straight run is reserved for a head, and a legend key of that role is the plain stroke; the three marker numbers are validated and ignored. Typst and TikZ reject a primitive that carries a marker with `E_VISUAL_CAPABILITY_UNSUPPORTED` (a relation whose terminals are both `none` carries none and is drawn there as a plain path); SVG draws it, PNG is that SVG and PDF is that SVG through ReportLab.

`timeline.relation.cornerRadius` (a Theme metric in px; absent or `0` keeps square corners) rounds the turns of an orthogonal relation route when Layout completes the path: each turn becomes a quadratic arc whose radius is `min(r, half the incoming leg, half the outgoing leg)`; a leg that meets a terminal keeps a straight run of the terminal's `headLength` (a round terminal centred on the endpoint needs none); a point that is not a turn is not rounded; an arc whose chords meet a mark, text or label the polyline cleared halves its radius until clear, down to square. Scene `points` stay the orthogonal polyline and `pathCommands` carry the arcs; SVG and PNG draw the same commands, and the arcs are registered as route obstacles beside the polyline. The bundled default Theme (`editorial-readable-default`) declares 4 px; other presets declare their own value or none (#1046).

**Node approaches (#1109 R2).** Layout routes arrivals before departures in
stable topological order; the cyclic remainder keeps declaration order. Public
primitive order remains the declared relation order. Among candidates that
pass safety, terminal completion and quality limits, prefer no overlap with
completed endpoint-adjacent segments at either resolved node instance, then
the declared entry preference, then fewer bends, shorter Manhattan length,
and stable port-pair order. A final pass lists every remaining positive-length
collinear overlap between two relations at the same node, including two
arrivals or departures, as `I_LAYOUT_RELATION_NODE_APPROACH_SHARED:` followed
by JSON containing `nodeInstanceId`, sorted full `relationIds` and `reason`.
Scene independently reports `E_SCENE_RELATION_NODE_APPROACH_SHARED`, or
informational `I_SCENE_RELATION_NODE_APPROACH_SHARED` only for an exact
diagnosed pair/node. Point contacts and unrelated instances do not count;
Scenes without endpoint identity are not inferred from coordinates.

**Same-port fan-in (#1109 R6).** Compatible arrivals at the exact same resolved
target port may share their final positive-length run and one target terminal.
Layout canonicalizes span `finish`/`end` aliases, distinguishes point cardinal
ports, and requires identical paint, terminal style and final approach direction.
It preserves every route and relation ID, assigns the first declared compatible
arrival as terminal owner, and removes only the other target markers. Headless
declarations remain headless; round terminals retain their semantic centres.
Completed `fanIn` identity is projected to Scene as specified in Spec 08.
Only these arrival pairs are excluded from node-conflict ranking and residual
diagnostics. Other ports, instances, incompatible heads, departures, mark/text
collisions and quality-limit violations gain no exemption.

**Bend reduction (#1109 R3).** Before quality limits and ranking, Layout
collapses monotonic collinear vertices and obstacle-free interior S-jogs.
Every reduction preserves exact endpoints, terminal entry/exit directions,
required egress/stub runs, completed terminal/stroke validity and full-route
obstacle/mark safety. Arbitrary original terminal-leg lengths are not minima.
Each reduction removes vertices; blocked reductions retain the safe detour.
All eligible finite port pairs are compared, with exact rank ties retaining
the first declared pair. Scene and adapters do not simplify geometry.

**Entry obstacles (#1109 R4).** A comparison-host corridor exempts only named,
physically connected marks of that endpoint. A detached snapshot or actual
mark remains an obstacle even when it belongs to the same object. Entry stubs
retain the whole target head plus at least one relation stroke width of clearance.
A legal full-radius stub (`headLength + max(cornerRadius, strokeWidth)`) remains
preferred; if that corridor is blocked, Layout offers the head-plus-stroke
minimum through the same collision checks. Rounded completion clips the turn
radius to the available pre-head run, counting that effective radius once and
never shortening the straight head tangent. Semantic side-entry recognition
uses the mandatory head-plus-stroke minimum. `entry-stub-blocked` is a
final reason when that complete corridor leaves the plot or intersects a
non-host mark, text or label. Layout never shortens the mandatory head-plus-stroke run.
When a legal side candidate loses to a clear node approach under the common
ranking, the final reason is `node-approach-conflict`, not search failure.
Entry success is determined on the accepted semantic corridor before round
terminals shorten the painted line; the head-occupied part still counts.

**Back-route source candidates (#1109 R4b).** The row-gap construction uses
the same finite, completed source egresses as ordinary routing, including
top/bottom exits for points and temporal-edge top/bottom exits for spans.
Each preserves its semantic port and connected comparison-host corridor;
its reserve is sized from the source terminal, not the target head. Layout
checks every completed candidate against plot bounds, primary-mark and text
safety, terminal/stroke fit, self-overlap and the unchanged quality limits.
Detour reference length joins the two mandatory corridor tips by Manhattan
distance and includes both corridor lengths. Rank by clear node approach,
then bends and length, preserving stable egress order for ties. A blocked
horizontal exit is not proof that the other legal egresses are blocked.

**Primary-mark safety (#1114).** In every row mode and entry policy, completed
relation paths MUST NOT traverse primary planned-mark interiors, including
their own endpoint marks. Interior bounds are inset by half the relation stroke
width to allow boundary ink contact. The exemption is terminal contact on the
outward side, never permission to route through the primary mark. A span's
far-side exit is not a candidate; start/end retain their temporal ports with
outward or above/below egress. Spec 33's named comparison-host corridor
exemption remains scoped to that corridor. This applies after repair, to
back-routes, rounded paths and diagonal visible-overflow fallbacks, superseding
the broad own-mark exemptions above. An unsafe direct fallback is suppressed
with `W_LAYOUT_RELATION_SUPPRESSED` and `I_LAYOUT_RELATION_MARK_BLOCKED:<relation id>`.
Lane attempts retain `E_LAYOUT_ROUTE_THROUGH_MARK` evidence. Scene observes
completed crossings as `E_SCENE_RELATION_THROUGH_MARK`; it does not repair routes.
Remaining candidate order, bounds and comparison semantics are unchanged.

Required, route-independent lane item names and deltas are measured and
registered as obstacles before semantic routes. A route body or endpoint
egress MUST NOT cross any required lane/member label; the named host-mark
egress exemption does not exempt text. Relation labels anchored to a completed
path are placed after that path, not misclassified as pre-route item labels.
Lane membership is already fixed from Project/View data (Spec 38) before this
placement phase. A label that cannot fit is suppressed with a source-keyed
count; its absence does not add, merge or split lanes. Only labels actually
placed become route obstacles.
The order is names, then routes, then post-route labels and relation labels
(#687). A name can leave a dependency no corridor (names in stacked lane rows
form a wall across the channel; this is the usual cause, not a name at a port),
so before the names are placed Layout rehearses the name and route phases on
private copies of the obstacle index. For each relation that rehearsal
suppresses or completes only as the visible direct fallback, and that has a
route when no member name is present, that route's segments are reserved as a
corridor (obstacle class `route-reserve`, one stroke width plus the router's
grid offset on each side) which member names avoid and routes, relation labels
and annotations ignore. The corridors are kept only if a second rehearsal
leaves a strict subset of those relations lost and suppresses no name that is
shown without them; otherwise nothing is reserved and the order is exactly as
before. A name that yields takes the next legal candidate of its declared
ladder under the unchanged association, host and reach rules, or is suppressed
with its typed fact; the declared ladder is never extended. A route still never
crosses a required label and a name never crosses a corridor. Reserving every
relation port, ranking `above`/`below` over `end`, and placing routes first were
measured and rejected (see the #687 design).
For lane mode only, a declared `visible-overflow` direct fallback is permitted
only if the completed path clears every required placed lane/member label.
Otherwise Layout suppresses it with the same generic warning and typed
per-port-pair cause evidence. This safety rule outranks visual overflow but
never feeds back into lane membership or label placement; non-lane fallback
behavior is unchanged.

For a suppressed lane relation, Layout retains one typed result per candidate
port pair in deterministic order: `egress-collision` with blocker identities,
`no-route-found` from a typed bounded-search outcome, or `quality-rejected`
with measured length/direct length/bends and the declared limits. A generic
`ValueError` is not a no-route result. The primary cause is the furthest stage
reached by any pair (`quality-rejected`, then `no-route-found`, otherwise
`egress-collision`); all mixed attempts remain inspectable. A rejected measured
attempt may also retain the bounded search disposition. A suppressed
placement has no path or accepted attempt; an accepted route has a completed
path and no suppression evidence. Layout retains the existing generic
suppression diagnostic and emits lane-specific, stable cause evidence; Scene
projects it without inferring or rerouting. Existing non-lane diagnostics and
Scene/SVG bytes remain unchanged. See the [L3b route-evidence correction](../design/issue-467-494-l3b-prelayout-route-evidence-correction-2026-09-27.md).

### 3.4 Groups and legend

**Text-sized header bands (#1283).** Layout Profile
`backgroundExtents.groupHeaderBand: text` uses the completed header-content
inline interval: band start through the last nonsuppressed measured text/run
end, including the leading `labelInset` or existing tab reservation. It adds
no trailing or symmetric padding and clamps the interval to the table column.
The existing text overflow policy and band block extent are unchanged. With
all runs suppressed the interval contains only its leading inset (zero width
when that inset is zero); missing horizontal content bounds fail with
`E_LAYOUT_BACKGROUND_EXTENT`. Folded-point completion updates only the text
band's block extent, retaining its completed inline interval. Other background
extents, group-decoration selection and vertical tag cells remain unchanged.
`text` is not admitted for other background roles. Layout owns the completed
Rect; Scene and adapters do not measure or fit the band.

**Horizontal header inset (#1284).** `groupHeader.labelInset` names a finite,
nonnegative font-size ratio. Layout places plain and role-marked header text
at the header band start plus that ratio times `groupHeader`'s font size;
absent keeps existing placement. Completed header-content bounds include this
leading inset and the measured, nonsuppressed text/run ends, without inflating
glyph bounds. Baselines, authored run gaps and untabbed visible-overflow policy
remain unchanged. A start tab requires the absolute inset to cover its
`tabInlineSize + tabGap`; an end tab requires inset plus its reservation not
to exceed the header width. Incompatible declarations fail with
`E_LAYOUT_GROUP_TAB_SIZE` at `/body/roles/groupHeader/labelInset`, reporting
the actual inset and required reservation. Negative ratios fail there with
`E_THEME_TOKEN_TYPE`. Vertical tags refuse this horizontal property there with
`E_THEME_ROLE_PROPERTY_UNSUPPORTED` and retain `tabGap`.

Horizontal plain and role-marked group headers centre the `groupHeader` role's
line box in `header_bounds`, using the same Layout baseline function as table
cells (#1271). Vertical tags and folded-point header extent allocation are
unchanged. Text may visibly overflow a short band; centering is not clamped.

**Row rules (#1270).** View `backgroundDecoration.rows: rules` opts in to one
horizontal rule at every item row's bottom, including each group's last row;
group header rows have no rule. Layout spans the full table-to-timeline extent,
independent of zebra-band extent. The `rowRule` semantic resolves the `row-rule`
Theme role's scheme stroke, opacity and strokeWidth; absent paint raises
`E_THEME_ROLE_REQUIRED`. This is a `DECORATION` with warning-only contrast.
For presentation-contrast corpus coverage, `row-band` and `row-rule` are the
two emitted alternatives for the required row-decoration concept; each emitted
role is still evaluated, absence of both remains a coverage error, and other
required decoration roles keep their independent coverage requirement.
Layout completes order 10 (not a Theme order knob), below grids at 11 and marks
at or above 100. Only actually emitted row/group/header bands must have order
below 10; a conflict raises `E_LAYOUT_ROW_RULE_ORDER` at
`/body/backgroundDecoration/rows`, with the conflicting role, actual order and
required bound. Unused roles are not rejected and Theme orders are never
silently rewritten. Undeclared row rules leave existing output unchanged.

View grouping gains `presentation: band | header`; `header` requires a non-zero resolved `timeline.groupHeader.blockSize`. Layout reserves one header block before the group's first row and supplies measured header text bounds spanning the selected table/timeline surface. Missing capacity completes visible stacked geometry and `W_LAYOUT_GROUP_HEADER_OVERFLOW`.

**Header text (#583).** `grouping.header` is an optional View template for the header text. It is usable only with `presentation: header` and grouping by `field` or `objectType` (`E_VIEW_GROUP_HEADER_UNUSABLE`). `text` (and the optional `first`, used for the first group in display order) is literal text with the closed placeholders `{ordinal}`, `{title}`, `{secondary}` and `{figure:<id>}`; `{{` and `}}` are literal braces and any other brace use is `E_VIEW_GROUP_HEADER_TEMPLATE`. `{ordinal}` is the group's 1-based position in display order in the form `ordinal`: `arabic` (default), `zero-padded` (width: the digit count of the group count, at least 2), `roman` (1 to 3999), `kanji` and `kanji-formal` (daiji; both 1 to 99); a position outside the form's range is `E_REVIEW_GROUP_ORDINAL_RANGE`, never a fallback. `{title}` is the group's entity title. `{secondary}` is the string in `entities.<group>.fields.<secondary.entityField>`, and the declaration and the placeholder must appear together (`E_VIEW_GROUP_HEADER_TEMPLATE`); a missing or empty value is `E_REVIEW_GROUP_HEADER_SECONDARY`. `{figure:<id>}` (#586) is the integer value of the derived figure of that id in the View's `figures` (Specification 06 section 7.2), in ASCII digits with a minus sign when negative and with no format specification; a global figure shows the same number in every header, while a `scope: group` figure resolves in the current group (Spec 06 §7.2), an id the View does not declare is `E_VIEW_GROUP_HEADER_TEMPLATE` (the message lists the declared ids), and a figure whose fact is missing refuses the render (Specification 05 section 12.2) rather than showing a blank. Content normalization composes the final text once and Layout places it as it places the title, so overflow follows the existing header rules. A View without `header` renders the entity title unchanged.

**Role-marked header spans (#1192).** A placeholder of the header template may name a Theme text role, `{name|role}` (`name` any placeholder above, `role` a letter followed by letters, digits, `_` or `-`); literal text is never marked, `{{` and `}}` keep their meaning, and a template without `|` parses and renders exactly as before (a `|` inside a placeholder was an error, so no existing template changes; the `heading` templates still refuse it). The marked placeholder's text is one run in that role's typography (family, weight, size, line height, letter spacing, transform, numeric spacing, compression, `viewerFit`) and ink (`fill`); adjacent parts of one role merge, and literal text and unmarked placeholders take `groupHeader` typography and, when the Theme binds `group-header.fill`, that ink (#1244; otherwise the `text` ink). A role the Theme does not declare, or declares without `fill`, is `E_THEME_ROLE_REQUIRED` at the View pointer `/body/grouping/header/text` (or `/first`) with the Theme pointer in the detail; a role named only by a header template counts as read for `W_THEME_ROLE_UNREAD` (#1117). Layout completes a marked header as one Text placement per run (`group-header:<group>#run<k>`, no `group-header:<group>` for that group), each measured with its own role's metric as its viewer sees it (transform applied, compression and letter spacing included), starting where the previous run and the gap before it end, all on one baseline that centres the `groupHeader` role's line box in the header block: top + (block size − font size × line height)/2 + font size (#1271); marked run typography does not change that shared baseline. Gaps are derived, never declared: whitespace at a run's edge is a gap measured in the face of the run it belongs to (one space is one gap, so `ACT {ordinal|r} · {title}` keeps its spaces; each gap also holds the letter spacing a single painted line puts after the glyph before the whitespace and after each whitespace character, so a letter-spaced role does not swallow the space (#1238); two spaces make a double gap; whitespace between two marked spans belongs to the unmarked text there; trailing whitespace is nothing), so the block's inline size is the sum of the run widths and the gaps. The header keeps its overflow rule: unbounded, as an unmarked header is, unless a group tab bounds it (#882); then the last run gives way first (`W_LAYOUT_TEXT_ELLIPSIZED` for that run, source kept), a run that cannot keep an ellipsis is suppressed with the same warning and the run before it gives way next. Scene emits each run as an ordinary Text primitive of purpose `group-header` and scene role the run's role, so the ground-text contrast gate judges every run's ink on the header band (a miss names that run's id), `viewerFit: text-follows-box` pins each run to its own measured width, and every adapter draws it as it draws any text; Typst and TikZ place each run at Layout's inline offset in the run's own size and ink, so with a face of other metrics the gaps drift unless the roles follow the box. Marked spans on a vertical `groupHeader` tag are refused (`E_LAYOUT_GROUP_HEADER_RUNS_VERTICAL` at `/body/grouping/header`): a vertical tag is one rotated label. A figure id may not contain `|` (`E_VIEW_FIGURE_INVALID`).

**Group tab (#882, #1166).** Theme role `group-tab` (semantic `groupTab`, purpose `group-tab`) declares one Rect per group, targeted at its header or vertical tag. `tabTarget` is `header` when absent and `tag` when explicitly selected; a Theme without the role (or declaring neither `backgroundTreatment` nor `backgroundPaintOrder`, or `backgroundTreatment: none`) keeps today's output and no View field exists. A `tag` target requires `groupHeader.writingMode: vertical`, with `E_THEME_TOKEN_TYPE` at `/body/roles/group-tab/tabTarget` even if the role otherwise would not draw. Explicit `tabInlineSize`, `tabBlockSize` or `tabPosition` are header-only and raise `E_THEME_TOKEN_TYPE` at their own role-property pointers for a tag target. The vertical tag's natural line-box is `fontSize × lineHeight`; its allocated column is that inline size plus `2 × tabGap`, preserving the natural line-box inside the plate's inset. For a tag target, Layout uses the allocated tag column and each group's completed `content_bounds` row span, then insets the cell on all four sides by `tabGap` (absent: 0); text uses the same inset cell and retains the existing half-em clear space at each block end. A missing shown header group produces no tag plate. For a header target, `tabInlineSize` (a positive named number in px; required when drawable), `tabBlockSize` (positive; absent: final header block size), `tabGap` (non-negative; absent: 0) and `tabPosition` (`start`, the default, or `end`) keep their existing behavior: a `start` tab stands at the inline start and header text begins after `tabInlineSize + tabGap`, while an `end` tab stands at the inline end and text keeps its start. Header bounds span table and timeline, so an end tab may stand outside a table-only band. Header-target sizing failures remain `E_LAYOUT_GROUP_TAB_SIZE`; tag-target negative gap or an inset leaving no positive drawable width or height is also a declaration-size error, not content overflow. The tag plate takes the role's paint order and `opacity`, is never tinted by `grouping.tint`, and may carry the role's catalogue pattern. A tab is its own background shape: opaque overlap follows existing policy, and intersecting translucent shapes remain `E_LAYOUT_BACKGROUND_OVERLAP`. As a `DECORATION` Rect it is gated against the actual ground beneath it; text is gated on the plate and, for a patterned plate, its substrate and ink (Specification 46 section 8). Typst and TikZ draw a solid or outline tab as an ordinary Rect and reject a patterned one with `E_VISUAL_CAPABILITY_UNSUPPORTED` (Specification 63).

**Group tint (#583).** `grouping.tint` (`{scale, domain?}`, grouping by `field` only: `E_VIEW_GROUP_TINT_UNUSABLE`) names a Theme `colorScales` entry over the group values (`domain` is a list or `firstAppearance`, the default: the groups in display order). It resolves through the same total mapping as a mark colour scale (Specification 60 sections 2 and 5.1: `E_PRESENTATION_SCALE_MAPPING`, `E_PRESENTATION_SCALE_VALUE` for a group outside a listed domain, `W_PRESENTATION_SCALE_NOT_SEPARABLE`). Layout reads no colour: Scene paint completion replaces only the visible channel of that group's `groupBand` and `groupHeaderBand` primitives (the fill of a solid treatment, the stroke of an outline treatment), keeping the Theme role's opacity, paint order and geometry. A band spans the table and the timeline when `backgroundExtents` says so, so the tint spans both. A group with no band under `groups: alternate` has nothing to tint. The completed tint is the ground the contrast gate reads for every mark, text (the header text is gated at the required 4.5:1 floor, Specification 46 section 8) and row stripe over it, and the band's own contrast against the canvas is gated as a decoration; a tint close to a row stripe, a mark or the canvas is therefore a gate finding, not a silent loss.

A group's background band and its header band share one selection decision under `backgroundDecoration.groups: all | alternate`: a group selected for a band is banded from its own header row through its own last content row; a group not selected carries neither band, so an unselected group's header is never painted as an extension of a neighboring group's band. `backgroundDecoration.groups: none` is the sole unconditional case: every group's header band still paints (the header-only decoration), independent of body selection. A row-decoration stripe (`backgroundDecoration.rows: alternate`) and a group band may cover the same extent; Layout paints row stripes after group bands so an opaque stripe is not hidden by an opaque band at the same declared Theme paint order.

Translucent background intersections remain invalid except one explicit
relation: an overlay of higher rank over an earlier background of lower rank.
The ranks are, in order, `rowBand`, `groupBand` and `groupHeaderBand`; a named
period's `periodBand` (#582); `calendarClosed`. The exception requires the
overlay role's Theme paint order to be strictly later than the lower role's;
ordinary source-over composition at those completed orders preserves both
signals. Equal-order overlaps, same-rank overlaps (two period bands, two
closed days, a header band over a row band) and every other translucent pair
still raise `E_LAYOUT_BACKGROUND_OVERLAP`. Layout validates the pair and order before
Scene projection; adapters do not decide which background is visible. The
legend's calendar key uses the same Theme role without inheriting the plot's
underlying bands.

**Closed days (#893).** Closed days come from the Project default calendar
(`project.calendar` resolved in `calendars`) and from nothing else. A Project
that declares none has no closed day and no exception day, so no `calendar-closed`
background is drawn; a declared calendar is unchanged. A Detail Profile legend entry with the
role `calendar-closed` is listed only when the View selects at least one closed
day: a key for a band that is not on the plot misleads. The entry is dropped where
the legend list is derived, so the legend slot is measured and drawn without it.

**Contrast severity (#995).** Perceptibility of what the surface draws splits by what the paint carries.
*Legibility* paint (a data mark, a state or ground text) loses information when it is faint, and *decoration*
paint is ground (closed-day and exception stripes, group, row and axis bands, tints, patterns, the note box, the
kind bar and accent). The floors that measure them (3.0:1 for marks, 4.5:1 or 3.0:1 for text, 1.10:1 for a
decoration) are **opt-in design constraints** (#1126): a Theme that declares nothing is only told, with a typed
warning (`W_SCENE_MARK_CONTRAST`, `W_SCENE_STATE_TEXT_CONTRAST`, `W_SCENE_DECORATION_CONTRAST` and the
ground-unsupported twins), and a Theme that wants a class held to its floor declares it in `contrastPolicy`
(`mark`, `stateText`, `groundText`, `decoration`, `unsupportedGround`: `none`, `warning` or `error`;
Specification 07) so the render fails on a miss. The class comes from the semantic registry, never from a slide;
there is no per-slide exemption. The repository holds the Themes it ships to the floors through
`conformance/contrast-opt-in.yaml`. The normative rule, the codes and the report are in Specification 46 section 8. A
weekend stripe at the owner-approved faint opacity is therefore a warning, and the marks that cross it are still
judged on its colour. Every free label is legibility paint (#980): the as-of label, member, axis, table, legend and
annotation text and the rest of the Text a surface draws are *ground text* judged at the required 4.5:1 on what truly
lies beneath them (canvas, band, chip, texture or pattern in both colours, region frame, as-of cone), so a label
that is illegible on a dark or patterned target fails the gate like any other text (Specification 46 section 8).

**The plot (#880).** The plot is the timeline slot down to the bottom of its last row (the last group's content when groups exist), and never past the slot; with no rows it is the slot. A slot is an allocation and the rows are the content, so a surface given more block room than its rows need has an empty strip under the last row. The ground (group and row bands) stops at the last row, and every overlay that spans the height of the plot ends there too: the full-height `grid-major` and `grid-minor` lines, each closed day, the as-of line and a period band (and the anchor of a `bottom` period label). Axis ticks and the axis rule are not plot-height overlays and are unchanged. A slot the rows fill is unchanged. Inline, the plot is the timeline slot: the scale is inset by what point marks protrude (#501), so the window maps to a range narrower than the slot, and the margin that leaves at each end belongs to the plot. An axis band cell, a closed-day cell or a period band that starts or ends at the window edge reaches the plot edge there (an axis band cell takes no `cellGap` on that outer end), so band, ground and axis rule end at the same edge. Positions inside the window (interval starts, gridlines, labels, marks, the as-of line) do not move, and a scale that fills the plot is unchanged. Layout owns the extent; Scene and adapters carry the completed primitives. A region frame (#889) around the timeline slot follows the slot's allocation, not the plot: inside a panel taller
than its rows the ground and every plot-height overlay still end at the last row and the strip below is the panel's own paper.

**Axis label containment (#1291).** Layout admits each transformed, measured
primary/secondary run only inside its clipped logical interval, the axis block
and the plot inline extent. A painted band for that interval in the primary's
native block lane also constrains the run to its completed cell, including
`cellGap` and the outer-edge rule above. Select that cell by primary block centre,
then paint/native emission order, independently of inline-centre fit; an inline
gap cannot bypass its containment guard. An equal calendar interval painted in
another block lane is not the label's cell and does not constrain it.
Paint-host attribution may cross units (month labels on a quarter band): the
topmost painted cell under the primary's centre is its host, ordered by paint
order then native emission order. Hosted text must fit that host's full box;
Layout never switches to a neighbouring cell to hide overflow. Without a painted
host the identity is absent, but logical containment still applies.

A non-fitting primary is thinned with `W_LAYOUT_AXIS_LABEL_THINNED`; its typed
outcome and suppression decision remain, but neither run, a visible target nor
a visible-overflow record is emitted. If only the secondary cannot fit, Layout
omits it with `W_LAYOUT_AXIS_SECONDARY_OMITTED` and recomputes the primary without
it; a surviving secondary shares the primary's host. Candidate summaries and
final placement use the same completed cell and admission geometry. This rule
supersedes axis `visible-overflow`, including rotated runs and both window
edges, without changing the window, tier/unit selection, regular thinning
cadence or colours. Scene and adapters carry completed bounds; they do not clip,
reformat, measure or expand the canvas to recover an axis label.

A selected named period (#582; Spec 06 §7.1) completes one `Rect` background:
placement id `period-band:<period id>`, `sourceRef` the period id, semantic
`periodBand`, slot `timeline`. Its inline extent is the period's half-open range
clipped to the View window and to the plot, mapped through the scale that places
marks; its block extent is the plot (above), as the calendar
closure's. Fill, stroke, opacity, an optional catalogue pattern and the paint
order come from Theme role `period-band` (`backgroundTreatment` and
`backgroundPaintOrder`, as the axis band); `backgroundTreatment: none` is the
explicit absent disposition. A Theme that omits the role while a View selects a
period fails with `E_THEME_ROLE_REQUIRED` at `/body/roles/period-band`; no other
role paints it. Every packaged Theme declares `period-band`, `period-label` and `period-label-chip` (#880): the band is a flat translucent tint (opacity 0.12 to 0.16) of the scheme's `accent` (`text` in the two print Themes), so it reads as a lighter highlighted window, never a hole; the marks, closed days and label on it are judged on the tint composited over the ground beneath it (#1013), and the label sits on a `surface` chip (#911). The packaged Themes bind these roles to the closed set of Color Scheme intents only: a binding to a scheme category would make `--preset X --scheme Y` fail for every View whose scheme lacks it, so a scheme override re-colours the band and no category or catalogue is required. The band is a background and never enters the obstacle index.
Contrast is measured as a decoration role at the 1.10 floor over the primitive
beneath its centre; a band below the floor, or over a translucent host that
cannot be measured, is a warning (`W_SCENE_DECORATION_CONTRAST`,
`W_SCENE_DECORATION_GROUND_UNSUPPORTED`) and never fails a render, Theme
resolution or the corpus gate unless the Theme declares
`contrastPolicy.decoration: error` (#995; Specification 46 section 8). The marks and
text that lie on the band keep their blocking floors on the band's colour, and
a translucent host beneath a mark or text is judged on the host composited over
its own ground (#1013; Specification 46 section 8), so a translucent band is read
as the colour it makes and a Theme need not paint it opaque; only a host whose
paint cannot be read stays `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`.

A shown deadline (#822; Spec 06 section 7.3) completes `Path` shapes from the View-shown deadlines the use case
carries on the projection, each with the Core's slipped verdict (`ReviewDeadline`; Layout compares no dates to judge
lateness). For every completed planned mark of the object (semantic `planned`; a snapshot or scenario mark and a point folded
into a group header never host one) the tick is the vertical segment at the deadline date, mapped through the scale that
places marks, centred on the mark and `markReach` times its block size tall (placement id `deadline-tick:<mark instance>`);
a slipped deadline adds the run, the horizontal segment from the tick's lower end to the planned finish clipped to the plot's
inline end (`deadline-run:<mark instance>`). Both carry `sourceRef` the object id, semantic `deadlineMark`, slot `timeline`
and paint order the mark base plus Theme `markPaintOrder`. A deadline outside the View window (the closed range, both
edges inclusive) is recorded as `I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:<object>` and a folded header point as
`I_LAYOUT_DEADLINE_FOLDED:<object>`. The paths are registered as `rule` obstacles, so annotation candidates avoid them as they
avoid the as-of rule; member labels and relation routes treat a rule as they treat the as-of rule and may cross it.
Contrast is gated as a `mark` role at 3:1 over the primitive beneath its centre.

A selected period's label (`label: {placement, overflow}`) is one request to the shared label engine that places the
as-of and member labels, built in the first pre-route phase: `top` and `bottom` anchor a zero-height strip on the plot
edge so the engine's `below` and `above` geometry centres the label on the band against it, `inside` anchors the band;
the candidate search, collision predicate, chip, and `W_LAYOUT_LABEL_SUPPRESSED` / `W_LAYOUT_LABEL_OVERFLOW` records are
the engine's. The placed label is a `text` obstacle for relation routes, relation labels, later member labels and
annotations. Its Theme role `period-label` is state text (`contrastTreatment` `required` 4.5:1 or `deemphasized`
3.0:1, checked against the scheme surface at closure and against the primitive beneath it, the chip when present, in the
Scene gate) and is opt-in: a Theme that selects no label declares none.

A Layout `legend` slot is the sole authority for legend geometry. When it exists, every selected legend entry emits one swatch and one measured label. When absent, there are no legend primitives. It is a resource choice, not a renderer fallback. Header or row capacity shortfall completes visible stacked/natural geometry and a warning rather than rejecting the surface.

## 4. Schema and normalization

Update View schema/normalizer for the label overflow field, relation object form, and grouping presentation. Update Layout Profile schema/normalizer for relation routing. Preserve legacy `relations: semantic` by ingress-normalizing it to `{mode: semantic, overflow: visible-overflow}`. Preserve existing boolean or shorthand labels through the existing ingress adapter and normalize before Layout.

No corpus identifier, canvas size, role name, or fixture chooses behavior.

## 5. Verification

Before Scene construction, `assert_surface_placement` verifies:

1. every completed primitive is inside Layout's completed canvas bounds;
2. table, axis, label, group header and legend placements satisfy their selected overflow policy and every visible fallback has a structured warning;
3. every accepted relation route meets its quality limits;
4. no semantic item has duplicate finish-delta text;
5. every present slot family has its required placements.

The completed-Scene contrast policy is a separate observer (Specification 46 section 8): text and mark misses
are errors of the corpus gate, decoration misses are warnings reported by the render and the corpus report (#995).

Tests cover each invariant with synthetic fixtures independent of corpus
projects. Corpus output demonstrates whether declared YAML reaches approved
design targets; it is not the oracle for the core rule. Byte identity proves
only an intended no-behavior-change slice. For behavior changes, regenerate
materializer evidence and review the Scene/SVG/PNG diff against the general
rule and target; never hand-edit generated output.

## 6. Migration

1. introduce internal request/placement records and migrate the current table/row/mark/axis geometry without behavioral change;
2. move label, relation, group and legend geometry out of Scene;
3. add feasibility diagnostics and schema normalization;
4. adapt synthetic fixtures and example presentation YAML without changing
   Project facts merely to satisfy a render criterion; and
5. regenerate expected SVG only through the public materializer after all automated and visual acceptance checks pass.
