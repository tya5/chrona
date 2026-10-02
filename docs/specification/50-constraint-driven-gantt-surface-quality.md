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

Layout routes between completed ports through deterministic orthogonal candidates. A route is acceptable when it stays in the timeline, avoids required obstacles, has at most `maxBends`, and its Manhattan length is at most `maxDetourRatio × directDistance`. It ranks candidates by crossings, length, bends, then lexicographic points. With `visible-overflow`, no acceptable route completes as the deterministic direct path plus `W_LAYOUT_ROUTE_FALLBACK`; explicit suppression creates `W_LAYOUT_RELATION_SUPPRESSED`.

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
`egress-collision`); all mixed attempts remain inspectable. A suppressed
placement has no path or accepted attempt; an accepted route has a completed
path and no suppression evidence. Layout retains the existing generic
suppression diagnostic and emits lane-specific, stable cause evidence; Scene
projects it without inferring or rerouting. Existing non-lane diagnostics and
Scene/SVG bytes remain unchanged. See the [L3b route-evidence correction](../design/issue-467-494-l3b-prelayout-route-evidence-correction-2026-09-27.md).

### 3.4 Groups and legend

View grouping gains `presentation: band | header`; `header` requires a non-zero resolved `timeline.groupHeader.blockSize`. Layout reserves one header block before the group's first row and supplies measured header text bounds spanning the selected table/timeline surface. Missing capacity completes visible stacked geometry and `W_LAYOUT_GROUP_HEADER_OVERFLOW`.

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

A selected named period (#582; Spec 06 §7.1) completes one `Rect` background:
placement id `period-band:<period id>`, `sourceRef` the period id, semantic
`periodBand`, slot `timeline`. Its inline extent is the period's half-open range
clipped to the View window and to the plot, mapped through the scale that places
marks; its block extent is the timeline slot's plot rows, as the calendar
closure's. Fill, stroke, opacity, an optional catalogue pattern and the paint
order come from Theme role `period-band` (`backgroundTreatment` and
`backgroundPaintOrder`, as the axis band); `backgroundTreatment: none` is the
explicit absent disposition. A Theme that omits the role while a View selects a
period fails with `E_THEME_ROLE_REQUIRED` at `/body/roles/period-band`; no other
role paints it. The band is a background and never enters the obstacle index.
Contrast is gated as a decoration role at the 1.10 floor over the primitive
beneath its centre, and a translucent host beneath cannot be gated
(`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`), so a Theme paints a pattern band
opaque or a translucent band over opaque bands only.

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
