# Scene and Rendering

**Status:** Proposed
**Depends on:** [06 View Model](06-view-model.md), [07 Style and Theme](07-style-and-theme.md)
**Owns:** renderer-neutral scene representation, semantic-to-primitive projection, coordinate mapping, renderer interface, and export boundaries.

## 1. Purpose

A **Scene** is the complete, derived visual description of one explicitly evaluated Chrona View. It converts a styled semantic View Projection into positioned visual primitives that a renderer can consume without reinterpreting project semantics.

```text
Project + Schedule + View Context
              ↓
        View Projection
              ↓
      Style roles + Theme tokens
              ↓
             Scene
              ↓
    SVG / canvas / tldraw adapter
```

Scene is a derived artifact. It is not the source of truth for dates, dependencies, comparison alignment, object identity, or layout intent. Editing a rendered SVG or an interactive canvas does not, by itself, edit a Project or View.

## 2. Invariants

- A Scene MUST be reproducible from explicit Project, Schedule, View, Style, Theme, render-context, viewport, and layout-metric inputs.
- Scene coordinates MUST NOT be authoritative temporal data. Temporal truth remains in the Project and the derived schedule.
- Every renderable Scene node MUST retain a stable scene identity and its semantic or View-local source identity.
- A renderer MUST NOT infer dependency semantics, plan-versus-actual alignment, or visual roles from geometry, colours, text, or layer order.
- Scene construction MUST preserve the distinction between semantic dependencies, explanatory arrows, semantic annotations, and presentation annotations.
- Missing inputs, unresolved tokens, unsupported scale profiles, or failed layout MUST yield diagnostics rather than renderer-specific silent defaults.

### 2.2 Layout, Scene, and renderer seam

Layout is the sole authority for measured geometry. It turns normalized content,
declared slots, Theme metrics, and View intent into completed placements: bounds,
baselines, marks, ports, label positions, route paths, and feasibility diagnostics.
Scene maps those completed placements to ordered renderer-neutral primitives and
z-order; it performs no measurement, coordinate search, lane allocation, or routing.
Renderer adapters serialize primitives only. They do not infer policy, reflow text,
or repair missing geometry. This is the single handoff defined by ADR-0031 and
specialized by Specification 50.

### 2.1 M27 public Review SVG binding

For a Render Context whose target is SVG, the public `render-review` application route
MUST build a completed `SceneSurface` from one `ResolvedPresentationInput` and the
resolved Layout Manifest, then invoke the SceneSurface SVG adapter. A reduced
intermediate Scene, an adapter that receives authoring resources, and a serializer
fallback selected by profile, example, or missing capability are invalid.

Every declared and present slot family is complete-or-diagnose: title, table,
timeline/axis, legend, notes, group details, observations, milestones, and summary
either emit their declared primitives or fail before output. Optional families are
absent only when their resolved input is empty and their profile contract marks them
optional. The SVG adapter validates primitive bounds and required target capabilities;
it does not silently clip a required label or substitute a literal policy value.

## 3. Scene inputs and output

### 3.1 Explicit inputs

| Input | Responsibility |
|---|---|
| Styled View Projection | Selected semantic items, resolved placements, lanes, order, comparison facets, visual roles, and annotation intent |
| Resolved Theme | Concrete token values for required visual roles |
| Render context | Explicit locale, output target capabilities, and other declared environment values |
| Viewport | Logical width, height, margins, and clipping policy |
| Layout metrics | Explicit text and marker metrics required for reproducible placement |
| Scene profile | Declared temporal scale, lane layout, routing, and collision policy |

No input may mean “use the local date”, “use the current branch”, “use the installed font”, or “pick a renderer default”. A consumer that needs such a value must bind and record it before Scene construction.

Target capabilities are requirements, not renderer hints. Before building a target
artifact, the coordinator compares required distinctions from the View/Style/Theme with
the Render Context capability declaration. If a required distinction—such as source
metadata, explanatory-arrow treatment, accessible text, or marker semantics—is absent,
it emits a stable capability diagnostic rather than silently degrading the output.

### 3.2 Output

A Scene contains:

- a logical viewport and coordinate system;
- an ordered tree of scene nodes;
- primitive geometry and token references;
- source and role metadata for each node;
- declared clipping and hit-test bounds where relevant; and
- diagnostics and an input manifest sufficient to explain the result.

A Scene MAY be serialized as a cache or inspection artifact, but that serialization is not the canonical Project format.

### 3.2.1 CLI output filename and target identity

For `render` and `render-workspace`, the CLI MUST resolve one target before
Draft closure construction. If `--format` is absent, a recognized output
suffix selects the target: `.svg` → `svg`, `.png` → `png`, `.pdf` → `pdf`,
`.typ` → `typst`, and `.tex` → `tikz` (case-insensitive). An extensionless
Draft output defaults to `svg`. An explicit `--format` MUST agree with a
recognized suffix. Unknown non-empty suffixes and recognized suffix/target
mismatches MUST be rejected before output creation, with diagnostics naming
the offending suffix and either its conflicting target or the recognized
suffix set. For `render-review`, the immutable Context
remains the sole target authority; `--format` may assert it, and the output
suffix MUST agree with it. An extensionless immutable output is allowed.
This filename convention is CLI ingress policy, never Scene or adapter
authority. The exact migration and diagnostic contract are recorded in the
[issue #469 design](../design/issue-469-output-extension-design-2026-09-26.md).

### 3.3 Resolved presentation input and identity boundary

The Scene Builder receives one immutable **ResolvedPresentationInput**.  It is derived
once by the coordinator from the View Projection, resolved Style/Theme, Detail,
Layout, Render Context, and target capability declaration.  It contains semantic
facets, visual roles, selected slot instances, measured text inputs, resolved
layout/routing policy, and the resolved logical bounds for every surface slot, row,
and derived lane track; it is not another persisted authoring resource.  A slot bound
is Scene input, not an adapter convention.

The input records one named **surface instance** for every public SVG route selected by
the coordinator.  `table-timeline`, `review`, and `minimal` each have their own title,
timeline, axis, and ordered row bounds; a surface may share a `scaleId` with another
surface but never borrows that surface's origin, width, day width, or row height.  The
Builder emits mark, tick, text, and connector bounds for the selected surface instance.
The adapter serializes those bounds and cannot derive date-to-x or item-to-y from
settings, viewport margins, or item order.

Each temporal or annotation projection has a `projectionInstanceId` composed from the
stable slot ID, source reference, semantic facet, and declared primitive purpose.  A
visual role may change paint or glyph choice, but MUST NOT rename or replace the
semantic facet.  Thus a planned mark drawn as a baseline remains `planned`, and an
Actual point remains `actual` even when they share geometry or paint.  `sceneId` is
derived from `projectionInstanceId` plus the primitive-purpose suffix.  Array order,
coordinates, renderer element IDs, and display text are not identity inputs.

`ResolvedPresentationInput` also contains one immutable `SurfaceContentInput` derived
before Scene construction. It contains only selected, normalized presentation facts:
ordered table-column IDs and per-object display strings; selected relation IDs with
typed endpoints; visible View annotations with typed anchors and purpose; ordered
project-note text; resolved legend entries and coverage text; and declared summary
panels with already formatted metric text. It also carries the closed template-value map
`title`, `windowStart`, `windowLastVisible`, `selectedCount`, `unmatchedCount`, and
`missingCount`; values are normalized strings and no additional key is accepted. It
contains no Project, View, Schedule, or
settings object and is not persisted. Missing optional families are empty collections;
missing required normalized content is `E_PRESENTATION_INPUT_INCOMPLETE`.

Layout converts this input into measured geometry, ports, obstacles, and track bounds;
Scene projects its completed placements into primitives. An adapter receives neither authoring resources nor a
semantic View Projection and MUST NOT recreate a scale, select a slot, choose an
anchor, measure text, assign a lane, calculate a row/track y coordinate, or resolve a route.
It MUST also not use a settings-derived `dayWidth`, margin, or row height as a fallback
for a completed surface instance; a missing required slot, row, mark, or primitive is a
stable presentation diagnostic.

### 3.4 Closed Scene manifest

The completed Scene contains one immutable, derived manifest with version
`chrona/presentation-scene-manifest/v0.1`. It is inspection evidence, not a second
authoring resource. Its closed fields are the resolved settings version, logical
viewport width and height, ordered selected object IDs, ordered declared font-asset
content identities, normalized content-family counts, and one ordered temporal-scale
record for each public surface.

Each surface-scale record contains `surfaceId`, `scaleId`, half-open Date-only
`domainStart` and `domainEnd`, `rangeStart`, `rangeEnd`, `origin`, and `unitRatio`.
For the initial linear profile, range is the usable timeline-slot interval after the
resolved inset, origin equals `rangeStart`, and `unitRatio` is logical scene units per
calendar day. A completed `SceneSurface` carries its own identical scale record so a
serializer that receives only that surface can preserve the evidence. Missing scale
evidence is `E_PRESENTATION_PRIMITIVE_MISSING`; an adapter MUST NOT reconstruct it
from viewport, settings, slots, or primitive coordinates.

The normalized content-family counts are exactly `relations`, `annotations`, `notes`,
`legendEntries`, and `summaryPanels`. They explain which optional inputs participated
without copying their authoring content. Diagnostics are an ordered immutable Scene
collection separate from the manifest; the initial successful profile emits an empty
collection. Manifest fields and diagnostics are never cache or semantic authorities.

## 4. Coordinate system and temporal scale

### 4.0 v0.1 Scene profile

A Scene profile declares layout policy, not geometry. The first Date-only profile is
intentionally closed so renderer adapters cannot silently choose a scale or routing
algorithm:

```yaml
# chrona-contract: historical
version: chrona/scene-profile/v0.1
kind: scene-profile
id: date-lanes
body:
  temporalScale: {domain: date, mode: linear}
  lanes: {mode: view-groups, itemStacking: stable}
  routing: {dependencies: orthogonal, annotations: avoid-lanes}
  collision: {labels: diagnose}
  layoutMetrics: required
```

`temporalScale`, lane ordering, routing, collision policy, and metrics identity are
inputs to the Scene cache key. A change to any of them may legitimately issue a global
`replaceScope`; a local Project or Actual change may not cite this profile as a reason
to replace unrelated Scene nodes.

### 4.1 Logical scene coordinates

Scene uses a renderer-neutral two-dimensional logical coordinate system: origin at the viewport's top-left, `x` grows rightward, and `y` grows downward. Coordinates, bounds, stroke widths, and spacing use declared scene units. A renderer is responsible only for converting those units to its target units.

The viewport, margins, clipping rectangle, and device-independent scene size are explicit inputs. Responsive resizing therefore constructs a new Scene; it does not reinterpret an existing Scene as a new schedule.

### 4.2 Temporal projection

A Scene profile maps the View's temporal window to the `x` axis. For the initial Date profile, the mapping is linear and monotonic:

```text
x = scale(date)
TemporalSpan [start, end) = [scale(start), scale(end))
TemporalPoint at = scale(at)
```

The scale domain, output range, origin, and unit ratio MUST be recorded in the Scene
manifest and in the matching `SceneSurface` scale record defined by §3.4. Human-facing
inclusive-end labels remain a renderer or View presentation choice; they do not change
the half-open geometry rule above.

Non-linear working-day compression, DateTime scales, discontinuous intervals, and zoom-dependent semantic aggregation require named future Scene profiles. They MUST NOT be inferred from a calendar or a renderer's axis widget.

### 4.3 Lanes and ordering

The View supplies lane membership and deterministic order. Layout assigns each lane a concrete extent and each item a concrete position within that extent under the declared layout profile. Lane geometry is presentation geometry, not Project containment.

## 5. Scene node model

### 5.1 Common node metadata

Every Scene node has:

| Field | Meaning |
|---|---|
| `sceneId` | Stable identity within this Scene, deterministically derived from the input identity and primitive purpose |
| `sourceRef` | Project stable ID, relation ID, semantic annotation ID, or View-local presentation annotation ID |
| `sourceKind` | The source category, including whether a relationship is semantic or explanatory |
| `roles` | Resolved Style visual roles |
| `tokenRefs` | Resolved Theme token names used by this node |
| `bounds` | Concrete logical bounds for clipping, accessibility, and hit testing |
| `zOrder` | Deterministic paint order |

One source may emit several nodes. For example, a planned span may emit a bar, label, baseline comparison mark, and accessible hit target. The `sceneId` must include a stable primitive-purpose suffix so a renderer can distinguish them without relying on array position.

### 5.2 Standard primitives

The initial renderer-neutral vocabulary is intentionally small:

| Primitive | Purpose |
|---|---|
| `Rect` | Span bars, bands, lane backgrounds, and callout boxes |
| `Symbol` | Point events, markers, and reusable semantic glyphs |
| `Path` | Dependency connectors, explanatory arrows, variance marks, and leaders |
| `Text` | Labels, notes, axis labels, and accessible text alternatives |
| `Icon` | Completed catalog-backed vector/raster icon for an existing semantic mark or label |

These five kinds are the closed public v0.2 primitive DTO. Grouping and clipping are
`SceneSurface`, slot, group, bounds, and viewport metadata, not additional primitive
kinds. `layoutRegion`, `layoutSlot`, `tableHeader`, `tableCell`, `axisBand`,
`groupSurface`, `summaryPanel`, and `routedConnector` are closed semantic `purpose`
families projected onto the four kinds; they are not Scene nodes of new kinds.
Primitives contain geometry, concrete paint, and metadata; they do not contain
scheduling rules. Renderers must not invent a composite convention independently.

### 5.3 Public-surface primitive closure

Each public SVG route is represented by one `SceneSurface`.  A `SceneSurface` is an
immutable ordered collection of its resolved slots, rows, groups, and primitives; it
is not a view of a shared adapter-private coordinate system.  The selected surface
is the only Scene input an SVG adapter may receive for geometry-bearing output.

Every primitive in a surface has the following required fields:

| Field | Meaning |
|---|---|
| `sceneId` | Stable primitive identity, including its surface instance and purpose suffix |
| `projectionInstanceId` | Stable `(slotId, sourceRef, semanticFacet, primitivePurpose)` identity; `sceneId` derives from it |
| `surfaceId` | The selected public surface instance |
| `kind` / `purpose` | One standard primitive kind and its closed rendering purpose |
| `sourceRef` / `sourceKind` | Stable semantic or View-local source and its category |
| `semanticFacet` / `visualRole` | Meaning and decoration independently; a missing facet is explicit rather than inferred |
| `bounds` | Concrete logical bounds; `Text` additionally carries the measured baseline and text payload |
| `optional` | Whether Output may omit this primitive under the declared optional-overflow policy |
| `zOrder` | Stable paint order within this surface |

Primitive payloads are a closed discriminated contract. `Rect` carries `bounds` and an
optional non-negative `cornerRadius`. `cornerRadius` is logical Scene geometry: it is
present on span comparison marks, is bounded to half the smaller Rect dimension, and
is absent on Rect families that do not declare rounding. An SVG adapter serializes it
as equal `rx`/`ry` and never re-reads `theme.bar.radius`.
`Text` carries `text` plus exactly one `TextLayout`. `Symbol` carries one completed
outline and its concrete `bounds`, painted by exactly one resolved `ScenePaint`; a
milestone whose Theme-bound shape is a multi-part glyph is represented as several
sibling `Symbol` primitives sharing `sourceRef`/`purpose`/`visualRole`/`bounds`, one
per painted part, in ascending paint order — not as one primitive with several
paints. Contrast and perceptibility evaluation treat a prior `Symbol` primitive at
the same bounds as possible ground for a later primitive's paint, exactly as they
already do for a `Rect`, so a glyph part painted over another part is checked
against that part's colour rather than against the canvas. `Path` carries at least two ordered logical
`points`; connector-like paths additionally carry `fromPortId` and `toPortId`, while a
tick may omit both port identifiers. `Path.bounds` is the exact union of its points,
and `Icon` carries exactly one completed normalized vector payload or immutable raster
payload/identity, concrete bounds, resolved paint where applicable, decorative flag, and
accessible alternative. Icon has no authoring asset path, catalog lookup, Theme, text
metric, or placement-policy field. Its placement is Layout-owned exactly as Text is.
including zero width or height. Paint is the completed `ScenePaint` payload defined
by Specification 46; `visualRole` is retained only as semantic provenance. Adapters
serialize completed paint but never re-open Theme/Scheme tokens or calculate a paint
property. A kind/payload mismatch is `E_PRESENTATION_PRIMITIVE_INVALID`, and an
adapter must not repair it.

`optional` defaults to false. It is true only for a label or annotation family whose
applicable Detail rule has `required=false`; generated children of that optional
annotation box inherit the flag. It is not inferred by an adapter from purpose names.

Projected comparison marks additionally retain `laneGroupId` and `stackIndex` as Scene
metadata. They do not alter row-aligned geometry, but every SVG adapter emits stable
`data-lane-group-id` and `data-stack` hooks from Scene. `data-lane-offset` may coexist
as derived inspection metadata; it is not a replacement for stack identity.

`projectionInstanceId` is the identity of one projected semantic/facet instance.
`sceneId` is the identity of one emitted primitive and equals that projection identity
plus its stable primitive-purpose suffix. Axis `(scaleId, level, naturalInterval.index,
slotId)` is source metadata used to derive a projection identity, never a second Scene
identity rule.

Stroke decoration remains Theme-owned and is selected by primitive purpose from the
completed resolved Theme. The purpose mapping is closed: ticks/major axis use
`axisMajor`, minor axis uses `axisMinor`, table frame uses `frame`, row rules use
`rowRule`, group separators use `groupSeparator`, and dependency/explanatory paths use
`dependency`. The selected token contributes color, opacity, width, and dash together;
mixing fields from different tokens or hard-coding a dash is invalid.

`layout.axis.tickUnit` and `tickStep` produce major ticks. When `minorVisible=true`,
Scene also derives boundaries of exactly the next finer level in the closed order
`year -> quarter -> month -> week -> day`. Boundaries coincident with a major tick are
removed; `day` has no finer level. The remaining `minor-tick` Paths use `axisMinor` and
carry no label. This is display subdivision only and does not change the temporal
window or Date-only semantics.

Missing Actual is an explicit conditional Scene family selected only by the
View-projected `due-unobserved` state. An incomplete but present observation
is not missing; a future unobserved item is not yet due. The family uses the
planned mark's due endpoint and the row's resolved Actual-bar band. A
pattern Rect is centered vertically in that band and uses the Theme-owned width and
height. A label's preferred x begins after that Rect plus
`layout.missingActual.gap`, or at the planned left edge when no pattern is requested,
and is vertically centered using the `missingActual` typography. For current
review surfaces, Layout measures it against the requested margin box, retains
its natural visible placement when no position fits, records the required and
available extents, and expands the completed canvas. Scene does not measure or
repair it. `label`, `pattern`, and `label-and-pattern` emit exactly the
families named by their modes. Label text is `detail.missingActualLabel`. It never
fabricates Actual semantics.

Finish variance is also a closed conditional family. A complete Actual finish yields
`variance-ahead` for a negative calendar-day delta, `variance-on-track` for zero, and
`variance-behind` for a positive delta. A non-empty but incomplete Actual mapping
yields `variance-unknown`, anchored at the planned finish; a wholly absent/empty Actual
mapping has no variance family; it receives Missing Actual only when the
View-projected state is `due-unobserved`. The marker's
x coordinate is the later of planned and complete-Actual right edges plus
`layout.variance.offset`; its width is `theme.varianceMarkerWidth`, and its vertical
bounds are the union of the planned and complete-Actual bar bands (the planned band for
unknown). The label's preferred x begins after the marker plus
`layout.variance.labelGap` and uses the `variance` typography. It follows the same
Layout-owned measured placement and visible overflow fallback as Missing Actual. `labelAlign`
aligns its measured top, center, or bottom to the marker bounds. Known text uses
`positiveSign` and `signedDaysSuffix`; unknown text uses
`detail.formatting.unknown`. `showZero=false` suppresses the on-track family.
Adapters do not derive status from text or color.

Each Detail label rule has one closed Scene target. `title` controls the existing
per-object item-title label anchored to the planned/baseline body; `planned-date` and
`actual-date` create formatted endpoint labels only when the named facet and endpoint
exist; `comparison-delta` controls the variance label; and `annotation-text` controls
placement of the authored annotation text box. Date labels use
`detail.formatting.date`, never host locale formatting. Rule array order breaks ties;
the first rule for an identical `(source, facet, endpoint)` target wins.

`required=true` retains an applicable label at a deterministic visible
fallback position if no preferred candidate fits; Layout records its overflow.
`required=false` permits omission only when an explicit optional clipping or
suppression policy selects it. A rule whose facet/endpoint is absent is
inapplicable, not an overflow.
Item/date/annotation labels use the declared finite candidate order and obstacle set.
Variance retains its conditional-family placement above; its measured margin overflow
uses the same required/optional decision. Absence of a rule does not delete authored
title or annotation text: those families default to required. Planned/Actual date
labels are emitted only by their explicit rules.

For the `table-timeline`, `review`, and `minimal` surface instances, Scene emits the
following I3 core primitive set before any adapter is invoked: one resolved heading
`Text` and, when Detail enables it, one resolved subtitle `Text`; one
axis-band `Rect` and one axis-label `Text` for each declared axis interval; one tick
`Path` for each declared tick; one planned/baseline/actual/variance `Rect` or `Symbol`
only when that semantic facet is authorized by the resolved projection; and one
item-label `Text` for every selected object.  Mark bounds use that surface's own
timeline and row bounds.  A span uses `[start,end)`; a point uses its exact `at`
position.  Actual, baseline, and variance primitives are never synthesized from a
planned placement.

Paint resolution is keyed by primitive kind and purpose as well as `visualRole`.
An axis-band Rect uses the resolved axis surface/stroke token as its background, while
its axis-label Text uses the resolved foreground text paint and the level-specific
typography. Likewise, a table-header-band Rect uses the table-header surface paint,
while table-column-label Text uses foreground text paint and table-header typography.
An adapter MUST NOT flatten these foreground and background mappings into one color per
role. Required foreground Text and its containing background MUST differ in resolved
color; equality is a failed presentation validation result, never an accepted invisible
label.

Table cells, group decoration, semantic dependency paths, annotation boxes/leaders,
legends, and summary panels are distinct primitive families.  They remain in the
Scene Builder's I3 completion scope and must be migrated in the documented order;
an adapter may not retain them as a private geometry exception.  This separation
allows the core axis/mark/text migration to be verified without falsely declaring
the entire surface complete.

The heading and subtitle payloads are formatted by the Scene Builder from the resolved
Detail templates and permitted values. Their primitive purposes are `title-text` and
`subtitle-text`; both carry a measured `TextLayout`. The adapter must not format the
Project title, View window, selection count, or subtitle wording. A group surface keeps
its group-derived `visualRole`; the resolved Theme token supplies both color and opacity,
and an adapter serializes both token values without choosing a fallback opacity.

The remaining I3 families are closed as follows.  `table-timeline` owns table frame,
header band, column-label Text, group surface/header, alternating row surface, row
rule, and one measured table-cell Text per selected `(objectId,columnId)`.  A selected
semantic relation owns exactly one `dependency-connector` Path with two Layout-completed
ports. A visible View annotation owns a completed box Rect or balloon Path, measured Text, and its declared completed connector, if any. A Project annotation selected by stable View reference supplies text and object identity to that View annotation; it is not duplicated in the notes slot. Unselected Project notes still own measured Text in the notes slot. Layout, not Scene, owns all ports and geometry under the [#466 candidate contract](../design/issue-466-candidate-placement-design-2026-09-26.md). A present legend slot owns its swatches, measured labels, and
coverage Text.  A present summary slot owns a panel Rect, measured header Text, and
one measured metric Text per declared metric. `review` receives its remaining
connector, annotation, and summary families only in I3-F. `minimal` receives its
remaining connector and annotation families in I3-F; it does not own a summary family.
No adapter may invent any of these families before its Scene family is emitted. A
review summary exists only when the review surface owns an explicit resolved `summary`
slot and the normalized input contains a declared panel. Review and minimal may also
own resolved optional layout slots in addition to their surface-specific
title/timeline/axis slots; copying an optional slot into the completed surface is Scene
construction, never adapter fallback.

Family presence is conditional only on an explicit resolved slot, visibility policy,
and authorized source.  Absence of an authorized required member is
`E_PRESENTATION_PRIMITIVE_MISSING`; an absent optional source emits no substitute.
Paths contain ordered Scene-owned points and endpoint port identifiers.  Text always
contains its one `TextLayout`; Rect/Symbol/Path bounds are the union of their emitted
geometry.  The deterministic z-order is: background/frame, bands/group/row surfaces,
rules and ticks, marks, table/axis/item labels, connectors, annotation boxes/text/leaders,
legend and notes, then summary.  An adapter serializes this order without sorting or
rerouting.

An adapter selects exactly one named surface and serializes its primitive fields.
It MUST NOT inspect authoring settings, source item order, dates, margins, day width,
row height, or a different surface to repair missing geometry.  A missing surface is
`E_PRESENTATION_SURFACE_MISSING`; a missing required primitive, row, or slot is
`E_PRESENTATION_PRIMITIVE_MISSING`.  Both diagnostics identify the selected
`surfaceId` and, where applicable, the expected primitive purpose and sourceRef.
The adapter never receives or consults `SurfaceContentInput`; it is consumed entirely
by Scene construction.

## 6. Projection rules

Scene construction follows a deterministic order:

1. Layout validates explicit inputs and resolves temporal scale, viewport, lanes, text, routes, and feasibility;
2. Scene projects completed placements to primitives and z-order; and
3. Scene emits the Scene, manifest, and ordered diagnostics.

This order is normative: neither Scene nor a renderer may perform a later placement,
remeasurement, lane, or route pass after Layout completes.

### 6.1 Planned, baseline, and actual geometry

Planned placement, Snapshot placement, and Actual observation may each produce separate primitives for the same stable object. Their source identity remains the same while their primitive purpose and roles differ. The Scene MUST NOT collapse them merely because their geometry coincides.

If a comparison is absent, unmatched, or semantically unknown, the Scene emits only the primitives authorized by the View Projection and the corresponding diagnostic or `variance-unknown` role. It MUST NOT fabricate an actual bar, completion date, or forecast.

### 6.2 Relationships

Semantic dependencies are projected from the selected endpoint placements and retain the `dependency` role. An explanatory arrow is projected from a View-local source and target anchor and retains the `explanatory-arrow` role. They use separate source kinds and must remain distinguishable even when a Theme intentionally gives them similar tokens.

An omitted relation endpoint may terminate at a declared non-rendered boundary only when the View Projection explicitly represents that boundary. Scene must not synthesize a hidden object or relationship to complete a path.

### 6.3 Annotations

The View declares an annotation's stable anchor and logical preference, such as above, below, start, end, or a named region. Layout resolves concrete offsets, callout bounds, leader paths, collision adjustments, and any connector bridge gap under the resolved Layout profile. Scene only projects the completed primitives.

Collision resolution may move a presentation annotation within its declared placement constraints, but must retain its anchor and produce deterministic output. If no legal placement exists, Layout emits a diagnostic and applies the profile's explicit fallback; it must not silently detach the annotation. Scene and adapters do not retry placement or routing.

## 7. Layout metrics, determinism, and diagnostics

Text wrapping, label collision, symbol size, and connector routing can change geometry. To keep a Scene reviewable and reproducible, those decisions use an explicit Scene profile and declared layout metrics. A renderer may perform final paint-time rasterization but MUST NOT reflow semantic layout or route connectors differently.

At minimum, Scene construction diagnoses:

- missing or incompatible temporal scale, viewport, or layout metrics;
- unprojectable temporal placement or out-of-window geometry;
- unknown source reference, role, or theme token;
- unresolvable annotation placement or connector route;
- overlap that violates the selected layout profile; and
- renderer capability gaps that would discard required semantic or accessibility metadata.

Diagnostics identify the source reference, scene profile, and affected primitive purpose when available.

## 8. Renderer interface and targets

A renderer consumes a completed Scene plus its resolved token values and returns a target artifact and diagnostics. Renderers may add target-specific metadata, but they must preserve Scene identity and source metadata wherever the target permits.

### 8.1 SVG

SVG is a deterministic export target. An SVG renderer maps primitives to SVG elements and maps `sceneId`/`sourceRef` into stable metadata attributes or an equivalent manifest. The SVG file is generated output; hand-editing it does not change Chrona semantics.

### 8.2 Interactive canvas and tldraw

An interactive canvas adapter projects the Scene into the canvas store and preserves a mapping back to `sceneId` and source references. The canvas store is not the Project source of truth. A user interaction becomes a later Application Architecture command that proposes a Project or View change, which must be validated against the relevant specification before a new Scene is built.

An interactive adapter initializes from a completed Scene and supports incremental
reconciliation through a **SceneDelta**. A SceneDelta is a renderer-interface value,
not a new canonical or derived semantic state. It has a base evaluation identity, a
target evaluation identity, source revision identities, an invalidation reason, and an
ordered list of operations:

| Operation | Meaning |
|---|---|
| `upsert` | Create or update one node while preserving its `sceneId` |
| `remove` | Remove a node no longer present in the target Scene |
| `reorder` | Change deterministic sibling order without replacing unaffected siblings |
| `tokenUpdate` | Change shared resolved token values without replacing unrelated geometry |
| `viewportUpdate` | Change explicit viewport or clipping state |
| `replaceScope` | Replace a declared affected group or whole Scene |

An adapter MUST apply a SceneDelta atomically only when its base evaluation identity
matches its completed Scene. On mismatch it retains the completed Scene and requests a
compatible delta or completed Scene. A whole-Scene `replaceScope` is valid only with a
declared global invalidation reason; it is not the default for a local semantic change.

SceneDelta survives the shared v0.2 foundation unchanged. Its `upsert` payload is one
of the four public primitive kinds above; surface-purpose metadata participates through
the same `sceneId`. A delta cannot introduce a fifth primitive kind or bypass completed
Scene validation.

### 8.3 Future renderers

Canvas, PDF, image, and presentation-file exports are possible targets if they can declare their capability limits. A target that cannot preserve a required distinction must report that loss; it may not erase it without notice.

## 9. Output capability successor

Every adapter target supplies `chrona/output-capability/v0.2` before construction. The
output manifest records its target capability profile, adapter version, evaluation
closure, and all loss diagnostics. SVG is the baseline; PDF, raster, canvas, and
presentation outputs are derived adapters with no authority to alter Scene or Project.
A missing required capability rejects the request; an explicitly permitted loss remains
visible as a stable diagnostic and manifest entry.

The v0.2 SVG adapter consumes all three Output fields. It rounds serialized numeric
coordinates only, using exactly `coordinateDecimals`; Scene geometry and routing remain
unrounded. SVG currently supports `fontPolicy=reference`. `embed` and `outline` fail
with `E_PRESENTATION_OUTPUT_CAPABILITY` until an output-capability profile supplies the
required font operation; they never fall back to reference silently.

For current review surfaces, Layout completes a canvas containing every
required primitive, including negative-origin and beyond-viewport geometry.
Scene and the adapter project that canvas without an out-of-bounds fit refusal.
An explicitly optional primitive may be omitted only by its selected Layout
policy; omission is whole-primitive, not coordinate clipping. In-bounds
primitives are identical under either disposition.

For measured table-timeline row/track requirements, Layout first enlarges
and re-solves the **whole** normal-flow allocation when possible, including
the table and timeline host slots and later siblings such as notes. Scene
MUST NOT carry a canvas-only expansion as a substitute for this known host
allocation. A starter Draft render is part of the release perceptibility
evidence: it is serialized and evaluated by the same pure Scene evaluator
used for committed Scenes. Any text-text intersection error fails that gate;
warning transport in an interactive Draft does not waive release failure.

## 10. Out of scope

This document does not define:

- editor commands, undo/redo, persistence of canvas state, or interaction policy;
- YAML/JSON syntax for View, Style, Theme, or Scene profiles;
- renderer implementation APIs or a choice of graphics library;
- DateTime, DST, resource leveling, cost, timesheets, tickets, or portfolio workflows;
- automatic actual-driven rescheduling; or
- reverse engineering Project semantics from SVG, pixels, or tldraw shapes.

## 11. Boundary to Application Architecture

Application Architecture may choose concrete layout engines, text-shaping libraries, SVG libraries, cache keys, and renderer adapters. It must implement this document's explicit-input, identity-preservation, reproducibility, and SceneDelta reconciliation constraints. Any new standard Scene primitive, scale behavior, or editable-canvas round-trip rule requires a versioned specification change rather than an implementation-only convention.
