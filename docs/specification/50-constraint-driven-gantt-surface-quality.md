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

For `ellipsize-with-source`, Layout allocates deterministic widths, produces ellipsized `TextPlacement` values, and retains full source text/provenance. `visible-overflow` produces `W_LAYOUT_VISIBLE_OVERFLOW` with required/available facts. Non-intersection is required only for an author-selected policy that requests it; a visible fallback may deliberately overlap rather than remove content.

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

`plot` creates ordered candidates at the eligible mark sides and ranks them against required table text, axis text, marks, accepted labels, required annotations, and viewport bounds. `auto` tries start then end in deterministic order. If no candidate fits, `visible-overflow` completes the first ranked candidate with a warning; explicit suppression remains an author choice.

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

For a `fill` lane surface, the preflight also measures the finite stagger
ladder's block demand for each lane name. Layout closes that demand into the
row's minimum before it distributes remaining block space. A suppressed name
must identify its lane, final block extent and either the exhausted host
capacity or the maximum useful block extent of its finite candidate ladder.
Only after that growth-limit proof may it report a geometric blocker as a
secondary cause. No assignable block space may be abandoned while that lane
can grow. This affects neither membership nor Scene projection.

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
This no-fit outcome does not claim that the visible-label acceptance
criterion was met; starter and HALCYON default cases must have a legal
plot-side candidate. Ordinary label requests retain their declared
visible-overflow fallback. Scene and adapters do not retry, move, clip, or
repair the as-of label.

For suppressed plot member labels, Layout MUST also count completed
`memberLabel` text placements with `overflow: suppressed` once per surface.
End-side member-name candidates cannot leave more than two times their
completed Text `fontSize` between their own mark's inline edge and their
Text bounds. When no end candidate fits within that bound, Layout tries
the declared start rung, then records suppression and the aggregate count.
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

Translucent background intersections remain invalid except an intentional
`calendarClosed` overlay over a `rowBand`, `groupBand`, or `groupHeaderBand`.
That exception requires the calendar role's Theme paint order to be strictly
later than the band's; ordinary source-over composition at those completed
orders preserves both signals. Equal-order overlaps, closed-day/closed-day
overlaps, and every other translucent pair still raise
`E_LAYOUT_BACKGROUND_OVERLAP`. Layout validates the pair and order before
Scene projection; adapters do not decide which background is visible. The
legend's calendar key uses the same Theme role without inheriting the plot's
underlying bands.

A Layout `legend` slot is the sole authority for legend geometry. When it exists, every selected legend entry emits one swatch and one measured label. When absent, there are no legend primitives. It is a resource choice, not a renderer fallback. Header or row capacity shortfall completes visible stacked/natural geometry and a warning rather than rejecting the surface.

## 4. Schema and normalization

Update View schema/normalizer for the label overflow field, relation object form, and grouping presentation. Update Layout Profile schema/normalizer for relation routing. Preserve legacy `relations: semantic` by ingress-normalizing it to `{mode: semantic, overflow: visible-overflow}`. Preserve existing boolean or shorthand labels through the existing ingress adapter and normalize before Layout.

No HALCYON identifier, canvas size, role name, or fixture chooses behavior.

## 5. Verification

Before Scene construction, `assert_surface_placement` verifies:

1. every completed primitive is inside Layout's completed canvas bounds;
2. table, axis, label, group header and legend placements satisfy their selected overflow policy and every visible fallback has a structured warning;
3. every accepted relation route meets its quality limits;
4. no semantic item has duplicate finish-delta text;
5. every present slot family has its required placements.

Tests cover each invariant with one neutral fixture and HALCYON regressions. Materializer byte checks remain required. PNG evidence at declared viewports is reviewed from generated output, never hand-edited.

## 6. Migration

1. introduce internal request/placement records and migrate the current table/row/mark/axis geometry without behavioral change;
2. move label, relation, group and legend geometry out of Scene;
3. add feasibility diagnostics and schema normalization;
4. adapt non-HALCYON fixtures and current examples; and
5. regenerate expected SVG only through the public materializer after all automated and visual acceptance checks pass.
