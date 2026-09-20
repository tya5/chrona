# I3 Public Surface-Adapter Completion Plan

**Status:** Design closure in progress. I3-A implementation starts only after this
plan, Specification 08 §5.3, the derived fixture, and the design review are published
and confirmed to be consistent.

## Goal

Constrain each SVG adapter for `table-timeline`, `review`, and `minimal` to serializing
a completed Scene. Remove, in stages, every adapter path that reinterprets dates, row
order, slots, margins, font measurement, lanes, routes, wording, or comparison facets.
This is an I3 correction; it adds neither a new renderer nor an authoring format.

## Designed input/output boundary

The only input is the single `ResolvedPresentationInput` from Specification 08 §3.3.
For every public surface, the Scene Builder emits slot/row/group/track primitives with
`sceneId`, `projectionInstanceId`, `surfaceId`, purpose, source, facet, role, bounds,
Text payload/baseline, and z-order. An adapter receives only its selected
`SceneSurface`, resolved token values, and target capabilities; it receives no Project,
Schedule, View, settings, or projected-item list.

The same `scaleId` shares normalized temporal positions only. A surface MUST NOT share
an origin, width, day width, row height, or title/axis/timeline bounds with another
surface. Missing data stops processing with the following diagnostics.

| Missing value | Diagnostic | Prohibited adapter recovery |
|---|---|---|
| Named surface | `E_PRESENTATION_SURFACE_MISSING` | Select another surface or generate from settings |
| Slot, row, or required primitive | `E_PRESENTATION_PRIMITIVE_MISSING` | Fill from margins, day width, or row order |
| Unprojectable facet | Existing facet/anchor diagnostic | Substitute `planned` |

## Migration order and publication boundary

| Unit | Scene Builder responsibility | Responsibility removed from adapter | Acceptance condition | Publication |
|---|---|---|---|---|
| I3-A | Surface-primitive DTO, identity, title/axis/tick/mark/item-label projection | None; contract tests only | The same semantic input has different surface geometry on all three surfaces; missing facets are not fabricated | Stand-alone implementation after design publication |
| I3-B | Materialize I3-A core primitives on every surface | None; verify Scene completeness | Axis, mark, and Text are unique surface primitives; missing rows/slots diagnose | Stand-alone |
| I3-C | Table/group/cell and dependency/annotation/legend/summary primitives | `table-timeline` coordinate, measurement, route, and wording generation | Gantt only serializes every primitive | Stand-alone |
| I3-D | Selection API that consumes I3-A core primitives for review | Review date→X, row→Y, axis/tick/mark/title/item-label calculation | Emits the same SVG semantic values without settings or an item list | Stand-alone |
| I3-E | Selection API that consumes I3-A core primitives for minimal | Minimal date→X, row→Y, axis/tick/mark/title/item-label calculation | Emits the same SVG semantic values without settings or an item list | Stand-alone |
| I3-F | Remaining review/minimal connectors, annotations, summaries, and table-specific families | Remaining private geometry above | No public adapter calculates geometry | Stand-alone |
| V1 | Input manifest plus structural, behavioral, and image evidence | Guessing at completion evidence | Verify setting variation, missing Actual, point items, multiple slots, long text, lanes, and routes through every path | I3 completion |

### Complete design closure for I3-C through I3-F

I3-C targets `table-timeline` only. It moves table frame/header/columns, groups/rows,
table cells, semantic dependencies, View annotations, project notes, and legend/coverage
into Scene primitives. Each table cell has identity
`(table-slot, objectId, columnId, table-cell)`; a connector has identity
`(relationId, fromProjectionInstanceId, toProjectionInstanceId, dependency-connector)`;
an annotation has identity `(annotationId, purpose, box|text|leader)`; legend primitives
use `(legend-slot, role, swatch|label)`; coverage uses `(legend-slot, coverage-text)`.
Text reuses I3-B `TextLayout`; the Scene Builder alone resolves ports, routes,
obstacles, and line wrapping.

Before I3-C, extend the shared DTO with closed kind payloads: `shape` for Symbol and
ordered `points`, `fromPortId`, and `toPortId` for connector-like Path primitives.
Ticks use ordered points without ports. Structural tests reject every kind/payload
mismatch with `E_PRESENTATION_PRIMITIVE_INVALID`; adapters never synthesize a missing
payload. This DTO closure is a design-only publication before I3-C implementation.

I3-D and I3-E add no primitive families. They reduce review and minimal, respectively,
to serializers that consume only their selected I3-A/B core. I3-F adds those surfaces'
connectors, annotations, summaries, and remaining surface-specific families using the
same identity rules. In every unit, an absent slot, `none` visibility, or absent source
emits no optional family. Only a missing required member of an authorized source stops
with `E_PRESENTATION_PRIMITIVE_MISSING`.

The fixed z-order is `background/frame → band/group/row → rule/tick → mark → label →
connector → annotation → legend/note → summary`. Adapters MUST NOT re-sort, measure
dates/rows/ports/routes/text, wrap table or legend text, or generate summary values or
wording. This section, Specification 08 §5.3, and the derived-fixture validator are
the design gate before every I3-C-and-later implementation.

If I3-B through I3-F reveals a need for a new primitive family, identity input,
TextLayout, port, diagnostic, or surface ownership rule, implementation stops. Close
Specification 08, Specification 30, the derived fixture, design review, and this plan
in the same design publication before returning to that unit.

### I3-B reopening: single-point display window

The first I3-B implementation found that the standard base value
`singlePointSpanDays: 1` could not contain measured month and item labels. This is a
Layout display-window contract, not an adapter width recovery. Specification 29 is
corrected so that the standard base explicitly uses seven days.
`presentation_scene_from_schedule` applies this value to the display window and stops
with `E_LAYOUT_REQUIRED_OVERFLOW:text` when it is insufficient. I3-B is not complete
until TextLayout is corrected on top of this published design.

The base-fixture revision also updates the preset `base.contentIdentity` to the
SHA-256 of the same revision, and the design validator checks it against the real file
digest. I3-B implementation validation cannot proceed when reference synchronization
fails.

## Completion criteria

1. Adapter function signatures and dependency graphs prove that they receive no
   authoring resource or settings.
2. Structural tests inspect each surface's completed primitive identity, bounds, Text
   payload/baseline, and z-order.
3. The same semantic input retains the same facet on all three surfaces while only
   surface-specific geometry differs.
4. Existing SVG goldens are checked for semantic values, source IDs, and bounds, then
   visually inspected.
5. Run the full regression suite, presentation design validators, and fixture
   validators; record the target SHA and remaining unmigrated scope.

Before I3 completes, a state where only metadata comes from Scene while SVG geometry is
adapter-private MUST NOT be reported as complete.
