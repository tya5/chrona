# I3 Public Surface-Adapter Completion Plan

**Status:** Reopened for V1 foreground/background contrast correction. I3-A through
I3-F and the manifest remain complete; final acceptance is suspended until regenerated
axis and table-header labels are visibly distinct from their backgrounds.

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
| I3-F | Review connectors, annotations, and summaries; minimal connectors and annotations; table summary family | Remaining private geometry above | No settings-backed public adapter calculates geometry or wording | Stand-alone |
| V1 | Input manifest plus structural, behavioral, and image evidence | Guessing at completion evidence | Verify setting variation, missing Actual, point items, multiple slots, long text, lanes, and routes through every path | I3 completion |

### V1 manifest closure

V1 uses the closed `chrona/presentation-scene-manifest/v0.1` shape from Specification
08 §3.4. The Scene-level manifest records settings version, logical viewport, ordered
selected object IDs, declared font-asset identities, the five normalized content-family
counts, and ordered scale records for `table-timeline`, `review`, and `minimal`.
Each completed surface carries its identical scale record because serializers receive
only `SceneSurface`. A record fixes surface/scale identity, half-open Date domain,
usable output range, origin, and logical-units-per-calendar-day ratio. The serializer
preserves those values in target metadata and may not derive them from settings, slots,
or primitive bounds. Scene diagnostics are an ordered immutable collection and are
empty for a successful initial-profile build.

The manifest is derived inspection evidence only. It does not persist selected content,
duplicate Project/View fields, authorize a renderer default, or become an input to
geometry. The implementation publication must prove that differently sized public
surfaces share the same Date domain while retaining their own ranges and ratios.

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

I3-C also closes the pre-existing editorial title path: Scene formats the Detail heading
and optional subtitle before measurement and emits `title-text` / `subtitle-text`.
The Gantt adapter does not retain Detail templates or title/window/count formatting.
Group surface paint serialization consumes the complete resolved token, including
opacity; retaining an adapter opacity default does not satisfy I3-C.
The application boundary includes the six closed Detail template values in
`SurfaceContentInput.templateValues`; Scene must not reverse-parse coverage wording to
recover counts.

Before I3-C, extend the shared DTO with closed kind payloads: `shape` for Symbol and
ordered `points`, `fromPortId`, and `toPortId` for connector-like Path primitives.
Ticks use ordered points without ports. Structural tests reject every kind/payload
mismatch with `E_PRESENTATION_PRIMITIVE_INVALID`; adapters never synthesize a missing
payload. This DTO closure is a design-only publication before I3-C implementation.

I3-C also introduces `SurfaceContentInput` at the application-to-Scene boundary. The
entry path normalizes table cells, relations, annotations, notes, legend/coverage, and
summary strings once; Scene Builder consumes that immutable DTO. An SVG adapter receives
neither this input nor Project/View/settings. Tests mutate each normalized family and
prove that only the corresponding Scene primitives change.

I3-D and I3-E add no primitive families. They reduce review and minimal, respectively,
to serializers that consume only their selected I3-A/B core. I3-F adds review
connectors, annotations, and summaries; minimal connectors and annotations; and the
table summary family using the same identity rules. Minimal owns no summary family. In
every unit, an absent slot, `none` visibility, or absent source emits no optional
family. Only a missing required member of an authorized source stops with
`E_PRESENTATION_PRIMITIVE_MISSING`.

For summary input, the normalized DTO uses
`(panelId, headingText, ((metricId, formattedText), ...))`. The application boundary
computes the closed M16 metric catalog and localization once. Scene uses IDs only for
stable identity and serializes the supplied heading/metric text; neither Scene nor SVG
rebuilds wording from IDs. Review owns a summary family only when its completed surface
contains an explicit resolved `summary` slot. The resolved-settings review entry may
accept the normalized DTO, but its serializer still receives only `SceneSurface`.
The minimal entry normalizes selected target-independent Scene relations into the same
DTO before Scene construction.

The fixed z-order is `background/frame → band/group/row → rule/tick → mark → label →
connector → annotation → legend/note → summary`. Adapters MUST NOT re-sort, measure
dates/rows/ports/routes/text, wrap table or legend text, or generate summary values or
wording. This section, Specification 08 §5.3, and the derived-fixture validator are
the design gate before every I3-C-and-later implementation.

### I3-F completion record

Starting from the published design parent `41a0462`, review now receives normalized
relations, visible annotations, and preformatted summary panels before Scene
construction; minimal receives target-independent Scene relations. The common Scene
Builder emits routes, ports, annotation geometry, and review/table summary primitives.
Review's resolved optional summary slot is copied into its completed surface. The
minimal entry accepts an optional normalized `SurfaceContentInput` for visible
annotations that are not target-independent `Scene` truth; when absent it normalizes
the Scene's selected relations. All three settings-backed public entry paths return the
shared serializer output, and the legacy
post-SVG summary helper rejects resolved-settings use instead of appending private
geometry. Structural tests cover review/table families, formatted wording, minimal
relation routing, and direct minimal-annotation input. The full suite passes with 175
tests and the four presentation design validators pass. Publication of this unit
precedes V1.

### V1 image preflight correction

The first V1 raster inspection rejected overlapping table cells, group headings, and
item labels. Scene now reserves header height for every header-bearing group mode,
places table-surface item labels through the shared finite candidate mechanism, and
routes around required Text obstacles while excluding only endpoint-owned Text during
connector entry/exit. The finite router includes resolved timeline boundaries, so a
legal perimeter path is searchable without leaving the surface. The verification
harness binds both Regular and Bold font assets. Controller Z and all five ASTER
outputs were regenerated only after semantic/source/bounds checks passed, and the
overview plus tall master PNGs were visually inspected. The full suite remains 175
tests. The Scene-manifest implementation and final evidence review subsequently close
V1 without changing those inspected pixels.

### V1 completion record

The manifest design was published at `666007acac8602350db5cbb633c017b35a0d7d2b`.
Implementation parent `b32b1237ee60a0da892372acc150009dc69c91b0` adds the closed
Scene and per-surface scale DTOs, serializer metadata, content/font/input evidence,
empty successful diagnostics, Japanese and explicit long-text cases, and regenerated
SVG inspection artifacts. The final suite passes 179 tests with two existing
`RefResolver` deprecation warnings; the complete conformance runner passes. The V1
acceptance review maps every required case to its specification, implementation, test,
and artifact. No I3 implementation scope remains.

### V1 contrast reopening

Post-publication inspection found that the serializer flattened the `month` and
`tableHeader` roles to one color for both background Rects and foreground Text. ASTER
therefore contained valid month and column-label strings that were invisible because
their `fill` exactly equaled the containing band. This invalidates the prior visual
acceptance conclusion but does not reopen Scene geometry or authoring ownership.

Before implementation resumes, Specifications 08/30 close kind/purpose-aware paint
mapping: axis-label and table-column-label Text use foreground text paint while retaining
their existing level/table-header typography; their background Rects retain the existing
axis/table surface colors. Add sample-independent contrast assertions, regenerate all
affected SVG/PNG/HTML artifacts, inspect every raster, then rerun the full suite and
conformance before restoring V1 completion.

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
