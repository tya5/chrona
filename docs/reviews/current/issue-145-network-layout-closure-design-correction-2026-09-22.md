# Issue 145 Network Layout-Closure Design Correction

## Trigger and decision

N145-1 and N145-2 established the v0.8/v0.3 resource names, a typed graph
projection, and a pure rank-and-route module.  Review of the merged code
against the Issue 145 design found that those slices do not yet establish the
surface-specific placement closure promised by the design: the current Scene
input requires the table/timeline source set for every surface, and the graph
composer accepts caller-selected node dimensions instead of measured network
text and declared network metrics.  It also does not apply the required
writing-mode transform or the existing placement-quality invariants.

No public dependency-network Context exists yet, so this is a completion
correction rather than a migration break.  N145-3 MUST close these gaps before
adding the HALCYON materialization.  It MUST NOT make Scene or a renderer own
geometry merely to work around them.

## Corrected closed input

`render_review` continues to execute one surface-neutral pipeline.  Its source
catalogue gains a `network` source for every invocation, populated from the
already typed `DependencyNetworkProjection` when present and otherwise with an
empty neutral input.  This is source registration, not a View-syntax branch:
the use case does not select an adapter, calculate ranks, measure text, route
an edge, or inspect raw relations.

`build_scene_input` derives the required source set exclusively from the
typed `projection.surface`:

| Surface | Required layout sources |
| --- | --- |
| `table-timeline` | `title`, `table`, `timeline`, `timeline-axis` |
| `dependency-network` | `title`, `network` |

The Layout Profile resolver receives the same available source catalogue, but
the Scene boundary rejects a required source set for the wrong surface.  Thus
a network Context cannot accidentally reserve table/timeline geometry, and a
timeline Context retains its current contract and bytes.

## Corrected network placement closure

The network composer receives only:

* typed `DependencyNetworkProjection`;
* the resolved `network` slot bounds and Layout routing policy;
* `MeasuredSources` network label runs and resolved Theme metrics; and
* the Layout Profile writing mode.

Theme v0.3 adds the closed metrics `network.node.minInlineSize`,
`network.node.minBlockSize`, and `network.rank.gap`.  `measure_sources`
measures each node title as a `network` text run using the declared text role.
Layout turns those measurements plus the declared minima into node bounds and
`TextPlacement` records (content, bounds, baseline, lines, typography, and
font asset identity).  It rejects insufficient inline/block capacity before
emitting a partial layout.  The composer owns the horizontal/vertical mapping:
ranks advance inline for horizontal writing and block for vertical writing.

The resulting `DependencyNetworkLayout` contains node rectangles, distinct
ports, completed/suppressed relation records, and measured text placements.
It is checked by the existing surface-quality primitives for viewport bounds,
node/text overlap, port validity, and route quality.  Scene receives no
measurement input for this route and therefore cannot recover missing geometry.

## Scene adapter and semantics

`compose_review_surface` becomes the narrow typed dispatcher already called by
the unchanged use case.  Its table/timeline adapter remains byte-compatible.
Its network adapter consumes only the completed network placement closure and
maps it through registry entries:

| Semantic | Primitive | Theme role |
| --- | --- | --- |
| `networkNode` | `Rect` | `network-node` |
| `networkEdge` | `Path` | `network-edge` |
| `criticalEdge` | `Path` | `critical-edge` |

Network title labels use the existing `Text` primitive and the completed
layout typography.  Scene neither branches on raw View syntax nor ranks,
measures, selects ports, routes, or reads graph relations.  No renderer,
closure, or target capability branch is introduced.

## Revalidated boundaries and acceptance

* Project/Scheduler still own relation and critical facts; View projection
  still filters/types them; Layout alone owns all geometry.
* The only `render_review` change is unconditional source catalogue
  registration.  It is not a surface decision and preserves closure reads.
* A focused structural test prohibits font measurement, routing, and raw
  dependency traversal from the network Scene adapter.
* Tests cover wrong-surface required slots, measured label closure, both
  writing-mode directions, overflow/quality diagnostics, and registry-only
  network primitive semantics.
* The HALCYON network Context, generated SVG diff, public materializer byte
  check, output-property gate, and full suite remain the final N145-3 gate.
