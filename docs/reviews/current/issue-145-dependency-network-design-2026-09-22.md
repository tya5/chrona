# Issue 145 Dependency-Network Surface Design and Architecture Review

## Decision

Chrona gains a second View surface, `dependency-network`.  It consumes the
same closed Project/Scheduler/View result as `table-timeline`, but has its own
typed View graph projection, Layout composer, and Scene projection adapter.
It does not introduce a second closure, use case, target renderer, or geometry
model.

The investigation invalidated one hypothesis in Issue 145: the existing Scene
module is not surface-dispatching.  `render_review` invokes
`compose_review_surface`, which requires table/timeline slots and directly
couples Scene construction to the timeline composer.  A narrow Scene surface
dispatcher is therefore a prerequisite.  It is not a renderer or use-case
branch: it selects a complete Layout-to-Scene projection adapter from typed
View surface intent.  This correction is required to make the claimed seam
real rather than to work around it.

## Contracts and migration

The successor resources are View v0.8, Layout Profile v0.3, and Theme v0.3.
This is an intentional atomic migration of all materializable public resources
and compatible Profile requirements; v0.7/v0.2 Theme/Layout documents are not
accepted as aliases by the successor parsers.

View v0.8 requires `surface` with one of:

```yaml
surface: table-timeline
# or
surface: dependency-network
```

Making the discriminator explicit is preferable to an implicit default at a
version boundary: a Context has one inspectable surface intent.  A migration
tool or authored v0.8 resource must spell `table-timeline` for existing views.

For `dependency-network`, `selection`, `grouping`, `ordering`, `comparison`,
and `rows` keep their existing View ownership and typed parsing.  `window`,
`axis`, `markers`, and `shading` are forbidden: they express time-scale
geometry that has no network meaning.  The first network slice supports the
primary plan, Snapshot, or one Scenario as the graph source selected by the
existing comparison contract; Actual observations remain available as facts
but do not make a second graph.  An author wanting two hypotheses must use two
Views, not overdraw an unreadable network.

Layout Profile v0.3 adds the closed `network` slot source.  A network View
requires `title` and `network`, and rejects table/timeline-only required slot
sets.  A table/timeline View retains its current `title`, `table`, `timeline`,
and `timeline-axis` requirements.  A combined Context is achieved by an
explicit future composite surface, not by placing two independently generated
surfaces inside one View; this preserves one surface's deterministic placement
closure.

Theme v0.3 adds `network-node`, `network-edge`, and `critical-edge` semantic
bindings plus declared network sizing/gap metrics.  Every public Theme migrates
atomically.  A missing binding remains a Theme contract error, never a
renderer fallback.

## Typed graph projection

View projection gains renderer-neutral records:

```text
NetworkNode(id, title, rank, order_key, critical, source_kind)
NetworkEdge(id, from_node, to_node, from_endpoint, to_endpoint, critical)
DependencyNetworkProjection(nodes, edges)
```

They are derived after the existing scheduler result and View selection are
known.  Project remains the authority for relation semantics; Scheduler remains
the authority for criticality.  View projection filters relations to selected
nodes, retains stable relation ids/endpoints, and assigns no coordinates.
Absent endpoints, cycles, and selected-node omissions are explicit typed
diagnostics before Layout.  No raw Project mapping, Scheduler result, YAML, or
Scenario mapping crosses into Layout or Scene.

## Layout composition

`compose_dependency_network_layout` is a Layout-owned pure composer selected
by the typed surface kind.  It returns the same Decimal placement closure and
quality invariants as the current surface:

1. validate a DAG over selected nodes; reject a cycle with a stable graph
   diagnostic rather than inventing a rank;
2. assign each node `rank = longest predecessor path`; roots are rank zero;
3. sort each rank by the existing typed View ordering key, then stable object
   id as the final tie-break;
4. measure node labels with declared Theme typography; allocate node rectangles
   and distinct input/output ports inside the `network` slot;
5. route each edge with the existing orthogonal router, using port rectangles
   as obstacles and recording either a completed path or an explicit
   suppression/diagnostic;
6. reject text overlap, node overlap, invalid ports/routes, and required
   geometry outside the viewport through the existing surface-quality gate.

Ranks advance inline in horizontal writing modes and block in vertical modes.
Layout owns this writing-mode transform.  Node and edge placement never leaks
into View, Scene, or a renderer.

## Scene and renderer boundary

The corrected Scene boundary has one small dispatcher:

```text
typed View surface → Layout placement closure → surface Scene adapter → SceneSurface
```

The table/timeline adapter preserves current byte-characterized behavior.  The
network adapter emits only existing primitive kinds: a node is a `Rect` and a
measured `Text`; an edge is a `Path`.  It obtains all purpose/role mappings
from registry entries `networkNode`, `networkEdge`, and `criticalEdge`.  Scene
does not rank, measure, choose ports, route, inspect relations, or parse View
syntax.  SVG and other renderers remain unchanged because they already consume
Rect/Text/Path and Theme tokens.

## Architecture consistency result

| Boundary | Owner and result |
|---|---|
| Project / Scheduler | Project owns dependencies; Scheduler supplies schedule and critical facts. No network algorithm enters either module. |
| View projection | Selects and types graph facts, with no geometry. |
| Layout | Sole owner of ranks, node bounds, ports, routing, collision, and writing-mode placement. |
| Scene | Dispatches a completed surface placement and maps it to registry semantics only. |
| Renderer | Serializes existing primitive kinds and validates declared Theme bindings only. |
| Use case / closure | Remain surface-neutral; they build one closed input and do not branch on network syntax. |

## Design acceptance scenarios

1. Identical Project/View bytes produce identical node rank/order, paths, and
   SVG bytes.
2. A reverse dependency chain ranks predecessors before dependents; unrelated
   nodes use the View ordering plus id tie-break.
3. A cycle, unavailable endpoint, or unrouteable required edge produces a
   stable diagnostic and no fabricated path.
4. A critical relation uses `criticalEdge`; a non-critical relation uses
   `networkEdge`; node criticality never changes geometry ownership.
5. Table/timeline public materializations stay byte-identical after the
   explicit resource-version migration.
6. HALCYON materializes a dependency-network context through the unchanged
   public materializer and passes the common output-property gate.
