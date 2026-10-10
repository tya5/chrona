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

Track alignment and comparison stacks (#1149, Specification 07) are completed
Layout geometry. A shared immutable band allocation supplies ordinary/folded
marks, row requirements and provisional/final lane footprints. Span-frame bounds
are distinct from point-symbol bounds; Scene emits their existing role identities
and completed ports without choosing alignment or recomputing stack gaps.

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

A semantic relation Path MAY carry paired `fromInstanceId` and `toInstanceId`
in Scene v0.7. These non-empty opaque IDs are Layout's resolved endpoint
instances, not port names or coordinates; Scene and adapters MUST NOT infer
them from primitive identifiers or proximity. They are optional inspection
metadata, require both endpoints and a Path, and do not alter adapter geometry.
Scene v0.6 is unchanged. Layout's node-approach policy is owned by Spec 50.

For approved same-port arrivals, a semantic relation Path MAY additionally
carry `fanIn: {targetPortId, terminalOwnerId}` in v0.7. Both identifiers are
non-empty and opaque. Layout completes the group and chooses its first declared
arrival as terminal owner; Scene MUST NOT infer ports or choose that owner.
The owner is a member on the same surface with the same target instance and
port. Only it may carry `markerEnd`; a headless group has none. All relation
IDs and completed paths remain present. Serialization validates references;
the Scene observer rejects invalid groups or incompatible approach directions
and paint with `E_SCENE_RELATION_FAN_IN_INVALID`. Only validated arrival pairs
are exempt from the node-approach overlap finding; departures never are.

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
Layout resolves any point-mark edge inset from the largest measured left/right
extent of selected planned and Actual point facets, including symbol, icon,
rotation and stroke geometry, relative to each facet's date anchor. A
provisional full-slot scale may be used only to measure those pixel
protrusions; final marks and all emitted scale evidence use the single inset
scale. With no selected
point facet there is no mark inset. This does not change the View's Date-only
domain: its start and end map to the inset range endpoints, so interval axes
and shading use exactly the same forward mapping as marks. A non-positive
usable range is a Layout error. Lane preflight and final surface composition
use the same range; an adapter never clips or repositions an endpoint point
mark to repair the scale.

The normalized content-family counts are exactly `relations`, `annotations`, `notes`,
`legendEntries`, and `summaryPanels`. They explain which optional inputs participated
without copying their authoring content. Diagnostics are an ordered immutable Scene
collection separate from the manifest; the initial successful profile emits an empty
collection. Manifest fields and diagnostics are never cache or semantic authorities.

### Relation terminal axes and sub-stroke jogs (#1109 R1)

Layout removes sub-stroke jogs without moving boundary ports, rechecks mark and
obstacle clearance and route budgets, and rejects candidates whose completed
terminal-trimmed polyline still has a segment shorter than its stroke width.
This concerns the route skeleton, not rounded-corner tessellation or terminal
outlines. Scene observation reports `E_SCENE_RELATION_SEGMENT_TOO_SHORT` for
violations, including a short whole path. Existing declared overflow and
suppression rules remain; corpus resources are not tuned to conceal failures.
For a short endpoint tangent, Layout completes the marker axis from the first
(source) or last (target) segment at least `headLength` long, or the selected
port normal (preferred when available). A round head's short terminal jog
must follow that normal or be removed with the same safety checks; otherwise
Layout tries another port. For nearby round heads on a straight route, Layout
may reduce setbacks and adjust their reference offsets to reserve a stroke-width
run under the heads while keeping both centres at their original ports.
The optional finite marker `angleDegrees` is Scene v0.7 data;
SVG serializes it as marker `orient`, without choosing geometry. Its absence
retains `orient="auto"`, also when the completed axis equals that tangent,
and existing marker identity and bytes. Scene v0.6 is
unchanged; v0.7 is extended in place under Specification 56 §3.2.

For derived terminal attachment (#1148), Scene v0.7 additionally carries optional
marker `units: userSpaceOnUse` and, for a stroked head, `strokeWidth`. Layout has
already placed the visible tip (or round centre) at its port; `attachmentOffset`
may be negative only in this physical-unit mode. SVG serializes these completed
values with visible marker overflow and the fixed butt/miter/limit-4 treatment.
Without `units`, the existing marker serialization and rendering remain unchanged.

Optional Scene v0.7 `strokeClip` (#1148) carries a completed finite `region`,
`outside` boolean and, except for native Rects, the exact closed `outline`.
Its `paint.strokeWidth` is already the doubled render width; adapters never
derive it. For a Rect without an outline, the clip uses that primitive's existing
bounds/radius. The clip applies only to stroke, not fill; any host clip applies to
both. Primitive opacity and shadow/glow apply once to the composed fill/stroke.
SVG serializes nonzero-winding luminance masks; unsupported adapters refuse the
feature explicitly. Absence preserves existing Scene fields and rendering bytes.

## 4. Coordinate system and temporal scale

### 4.0.1 Theme catalogue patterns (#496)

Catalogue-backed pattern bindings use the current Theme contract and complete into Scene
v0.7. Layout owns the patterned region bounds, clip bounds, and tile origin.
For a patterned Rect, the repeated region is that Rect's completed bounds;
the tile origin is its inline/block top-left, and the clip is the same bounds
(including the Rect's completed corner shape when present). This fixes the
repeat phase per primitive, independent of SVG document origin or paint order.
Scene carries normalized tile primitives, angle, density, origin, clip bounds,
and completed `ScenePaint`; `paint.fill` is the substrate and `paint.stroke`
is the ink. Circle primitives may select ink/substrate/no fill and carry an
ink stroke; fill precedes stroke and primitive order is painter order. Each
tile is clipped before repetition. `densityBasisPoints` measures final visible
ink, not hidden ink or neighbouring copies (Specification 64 section 8).
Substrate operations require opaque completed fill and refuse ink-only paint
completion before a Scene is returned. PatternGeometry carries no color. No catalogue reference, Theme
token, target syntax, or source document crosses into Scene. The adapter may
encode repetition using SVG's user-space pattern syntax, but all tile values,
angle, origin, and clip bounds come from Scene. PNG consumes that same SVG via
the pinned resvg route. The adapter does not look up assets, alter geometry,
choose clipping, recolor, or select a fallback.

The contrast gate checks substrate against the actual host ground and ink
against both substrate and host ground; the minimum pairwise ratio must meet
the semantic floor (3.0:1 for marks, 1.10:1 for decorations; a mark below its
floor is an error, a decoration below its floor is a warning, Specification 46 section 8). The existing
opaque representative-ground rule applies to all three colors. Perceptibility
inspection receives the same channels and geometry/density facts; it does not
reconstruct effective paint from the catalogue.

**Glow (#587).** `ScenePaint.glow` is the completed halo
`{color, blur, opacity, fidelity, region}` (Specification 63 section 7); the
adapter serializes it and decides nothing, and a Scene that carries one is
`chrona/scene/v0.7`.

**Hand wobble (#588).** `ScenePaint.wobble` is the completed perturbation
`{amplitude, wavelength, seed, fidelity, closed, outline}` (Specification 63 section 8):
`outline` is one closed polygon for a Rect or one open polyline per sub-path for a Path.
The primitive's bounds, points and commands are not changed; adapters draw `outline`
verbatim, and a Scene that carries one is `chrona/scene/v0.7`.

**Canvas texture (#587).** A Theme that declares the role `canvas-texture`
(Specification 07 section 5.2) adds one Rect primitive to every Layout-completed
surface (table-timeline and dependency-network). Layout completes it: the Rect
is the completed canvas, the tile origin is the canvas top-left, and the Rect
belongs to the pseudo-slot `canvas` (source `canvas`, bounds the canvas), which
exists in the Scene slot list only for such a Theme. Its identity is
`canvas-texture`, purpose and visual role `canvas-texture`, paint order 0, and it
is the first primitive Scene emits, so it paints below every other primitive
whatever paint order a band or mark declares. It is an ordinary patterned Rect:
scene v0.7 carries it, SVG and PNG paint it, Typst and TikZ reject it, and no
Scene field is added. The contrast policy and the perceptibility observation
`I_SCENE_PAINT_CONTRAST` treat its substrate and ink as the ground of what lies on
it: a mark or state text is measured against the worse of the two
(`groundKind` `texture-substrate` or `texture-ink`), a decoration tint against the
substrate, and the texture itself has no floor.

**Transparent canvas treatments (#888).** Layout completes an ink-only texture
as the same clipped periodic geometry, with no substrate paint. It is sparse
ink, never an opaque host by canvas bounds. Layout also completes the full-canvas
bounds/clip and pseudo-slots for `canvas-overlay-gradient` and `canvas-overlay`;
neither enters obstacle allocation or changes content geometry. Their placement,
slot, source and role identities are respectively `canvas-overlay-gradient`
and `canvas-overlay`, with purposes of the same name and no contrast class.
Scene owns their paint relation: after projecting all content, emit the radial
overlay at one above the greatest content paint order, then the patterned
overlay one above that. Adapters do not infer or change this order.

Optional Scene v0.7 `paint.radialGradient` carries completed `{center, radii,
stops, fidelity}` with positive inline/block radii and ordered colour/opacity
stops. Layout owns centre/radii and offsets; Scene resolves Scheme colours and
opacity. Linear `gradient` and `radialGradient` are mutually exclusive. The
extension follows the optional glow/wobble/stop-alpha precedents: existing
Scene documents and absent-field serialization remain unchanged; v0.6 is not
extended. Patterned overlays reuse existing completed pattern data and carry
no algorithm, seed or resource lookup to an adapter. SVG serializes the layer
with `pointer-events="none"`; the independent interaction layer stays usable.
PNG consumes that same completed SVG. Omission and admission are Spec63 section 1.1.
Contrast and perceptibility consume the same ordered overprint pairs (Spec46),
not an adapter-derived raster or a flat-canvas-only proxy.

**As-of light cone (#890).** When the Theme declares the role `as-of-cone` and the
as-of marker lies in the window, Layout completes one closed polygon beside the as-of
line it already places: apex at the top of the line (the as-of x, the plot top), a foot
at depth `coneExtent` times the plot height (the plot ends at the last row, #880) and
half-width `coneSpread` times that depth, clipped to the plot's inline extent
(Sutherland-Hodgman against the two vertical plot edges), coordinates rounded to
1/1000 px, vertices in order from the apex, no trigonometry. A clip that leaves no area
gives no cone. Layout gives it paint order 50 (above the row, group, calendar and
period bands and the axis rules at 10 to 12, below every mark from 100, the as-of line
and all hosted and foreground text) and does not register it as an obstacle. Scene emits
it as one `Symbol` with purpose and visual role `as-of-cone` (source `actual-set`) and
completes its paint: a `LinearGradient` from the polygon's apex row to its foot row
with two stops of the role ink at stop opacities 1 and 0, and the role strength as the
paint opacity. Where the selected profile cannot paint a gradient the cone is omitted
whole (Specification 63 section 9). SVG writes `stop-opacity` on each stop of a gradient
that carries stop opacities (the gradient identity includes them; any other gradient is
byte-identical); PNG is that SVG through resvg. A Scene that carries stop opacities is
written as `chrona/scene/v0.7` (optional `opacity` on a gradient stop).

**Region frames (#889, #1165).** Each declared frame whose selected Theme role exists adds one Rect
primitive to the table-timeline surface. Layout completes it (Specification 33 section 3): the Rect,
its corner radius, and the pseudo-slot `frame:<node id>` (source `frame:<node id>`, bounds the Rect) that
owns it, which exist in the Scene only for such a Theme. Its identity is `region-frame:<node id>`,
its purpose is `region-frame`, its completed visual role is `region-frame` or `region-frame-<paint>`,
its paint order 0, and Scene emits the frames right after
the canvas texture, a container's frame before its children's, and before every other primitive, so a
panel paints below bands, rows, gridlines, marks and text whatever paint order those declare. It is an
ordinary Rect (a catalogue pattern makes the Scene v0.7, as for any patterned Rect): SVG and PNG paint it,
Typst and TikZ draw a plain one and reject a patterned one, and no Scene field is added. A frame is an
allocation, not a plot-height overlay: it follows the node's bounds, and the plot rule of Specification 50
is unchanged inside it.

The independent catalogue border (#888) projects each Layout `frameGlyph`
batch to `Symbol` parts named `frame-glyph:<node id>:part<n>`, purpose
`frame-glyph`, selected `frame-glyph[-<paint>]` role, pseudo-slot
`frame-glyph-slot:<node id>` and paint order 0. Each node's panel then border
precedes its children's frames and all content; all parts remain in one layer.
Scene admits or omits the entire typed batch before projection (Specification
63 section 10.1), never reconstructing its run, paths or fit. Parts use only
their completed fill/stroke paint intent; sparse ink is not a bounds-sized
ground (Specification 46 section 8). No new Scene primitive or public field
is introduced.

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

### Annotation note contrast ground

Hosted note-number text carries a completed `hostPlacementId` naming an
actually emitted mark primitive. For a Theme glyph, Layout resolves the
abstract mark to its first painted lane-emission part before Scene projection;
Scene does not choose or invent that part and rejects a dangling host.

The semantic registry classifies `annotation-note-text` as state text and
`annotation-note-box` as decoration. In the completed paired annotation,
Layout/Scene paint order places the box before its text. Contrast evaluation
does not infer a background-treatment absence from decoration classification:
only an explicit Theme `backgroundTreatment: none` yields an absent-decoration
disposition; a painted note box is an emitted witness. Contrast evaluation
uses the topmost prior opaque Rect or Symbol containing the text's policy sample
point as its ground; this is the note box when paired. The box fill is the
Theme-declared representative content-area color, including when its
`annotationContainer.outline` is `image`, as defined in Specification 07 and
the [#465 image-container design](../design/issue-465-image-annotation-container-design-2026-09-27.md).
Perceptibility consumes the same completed fill. It does not sample the image
payload, and the image's pixels do not replace the declared representative
ground. Findings identify the selected ground primitive and color.
A note box sized by `annotationContainer.inlineSize: fill` (#1051, Specification 07) is an ordinary completed Rect or Symbol at its final bounds; contrast and perceptibility judge it exactly as a content-sized box.

A box role's viewer-fit mode (#1050, Specification 07) is completed Scene data, measured by Layout and only serialised by adapters: a box primitive (a `Rect`, or the `Symbol` outline of a balloon or tilted note) carries `viewerFit` (`text-follows-box` or `box-follows-text`), and each text of the box carries `textLayout.fit`, written only when the role is not `raw`. For `text-follows-box` the fit is `{mode, adjust, lineInlineSizes}` with one positive measured inline size per line; for `box-follows-text` it is `{mode, boxId, endPadSpaces}` and the box and the text name each other one to one (a Scene that does not is `E_PRESENTATION_PRIMITIVE_INVALID`). `scene_document` writes a document that carries either as `chrona/scene/v0.7`; the optional properties are added to `scene-v0.7` in place (Specification 56 section 3.2) and Scene v0.6 is not edited. The box keeps its measured bounds and its paint in every mode, so the contrast and perceptibility gates judge it exactly as a `raw` box. **SVG** writes `textLength` (the line's measured size divided by `horizontalScale`, because the value is in the text's own pre-transform frame) and `lengthAdjust` on each line (on the `<text>` for one line, on each `<tspan>` for several); for a box that follows its text it writes, at the box's paint position, one `<g data-viewer-fit="box-follows-text" filter="url(#fit-<hash>)">` holding an invisible `<rect fill="none">` (from the box start to the text start, over the box block extent, at least 1 px wide) and the text with `xml:space="preserve"` and `endPadSpaces` trailing spaces on every line, and no static background rect; the filter is `x="0" y="0" width="1" height="1"` on the object bounding box with an `feFlood` of the box fill under `SourceGraphic`, one per distinct fill and opacity (a box with no fill has no filter). **PNG (resvg) and PDF (svglib)** are produced from the `raw` serialization (`render_v05_svg(surface, viewer_fit=False)`): the packaged font is fixed, resvg and svglib differ in their `textLength` and filter support (svglib ignores filters, which would erase the background), and a fixed output must not depend on a rasteriser's bounding-box computation. **Typst and TikZ** draw the box rect and the lines as `raw` and the render reports `W_VIEWER_FIT_NOT_HONOURED:<box role>:<target>` once per role (neither has a verified way to pin a run's advance or size a box from a rendered run). Measured (not claimed for every viewer): in headless Google Chrome without the layout face and in resvg 0.48.1, `textLength` pins a run in both adjust modes, on `<text>` and `<tspan>`, under rotation and compression, and the filter group ends the background at the rendered text (work record, section 8). Not verified: Firefox, Safari, GitHub's image proxy, PowerPoint or Keynote imports. A consumer that ignores `textLength` shows `raw`; one that ignores SVG filters shows no background for `box-follows-text`, the reason `text-follows-box` is the recommended mode. The SVG still names the family and does not embed it (#362).

The text of a chip or of a box-less text role (#1096, Specification 07) carries the same `textLayout.fit` (`text-follows-box` only) and no `viewerFit` box member; Typst and TikZ report `W_VIEWER_FIT_NOT_HONOURED:<Scene role>:<target>` once per Scene role that carries a fit, whether it is a box or a text run, and draw raw.

A box border (#1049, Specification 07) is completed by Layout: each bordered side is a `Rect` (no bordered neighbour) or a mitred polygon `Symbol` from the `annotation-border-<side>` or `annotation-kind-accent` role, lying on the box edge at full length, painted after the box and any artwork and before the kind frame and the text. SVG (and PNG and PDF, which rasterize the SVG) and TikZ draw a `Rect` and a polygon `Symbol` outline (TikZ maps a quadratic segment to a cubic with the control point repeated, which bulges a short arc by a few percent); Typst draws Rects and Text only and refuses a surface that carries any `Symbol` (`E_VISUAL_CAPABILITY_UNSUPPORTED`), which includes a mitred or rounded border strip, a tilted box and a balloon; none decides a mitre.

A rectangle container with a corner radius (#1087, Specification 07) is a `Rect` carrying `corner_radius` (a tilted one a closed rotated outline `Symbol` of quadratic segments), and each border strip a polygon `Symbol` of arcs painted after the box and any artwork; SVG, PNG, PDF, TikZ and Typst draw the `Rect` radius (`rx`, `radius`, `rounded corners`), the Symbol outlines are as stated above.

For `annotation-note-text`, the generic ground search is not sufficient by
itself: a prior Rect with no fill is skipped and generic search may then select
a lower host or canvas. C4 therefore requires `contrastTreatment: required`
on typed and serialized note-text primitives; missing or weaker treatment is
invalid even if a generic state-text evaluator would allow a 3.0:1
`deemphasized` case. C4 also requires a prior `annotation-note-box` with the
same `sourceRef`, containing the note text's sample point and carrying
opaque flat fill. Missing pair/fill or non-opaque fill yields
`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`; it cannot fall through to another host
or the canvas. This pairs the reported ground with the declared content area
and prevents a plausible but false contrast result. SVG, PNG, and typeset adapters
serialize the completed box/image/text paints without inspecting pixels,
selecting a ground, or repairing contrast. Geometry and image tile placement
remain Layout/Scene facts.

Independent numbered annotation-list status/summary records (#1130) use the
`annotationListText` binding: purpose `annotation-list-text`, shared `text`
paint, existing annotation typography and `GROUND_TEXT` contrast. They have
no note box or required leader: evaluate their actual underlying rail ground.
They are not `annotation-note-text`; boxed note prose retains C4 unchanged.

The annotation kind header (#584, Specification 07) is completed by Layout as separate shapes and text beside the annotation box: `annotation-kind-bar:<id>` and `annotation-kind-accent:<id>` Rect primitives (purposes `annotation-kind-bar` and `annotation-kind-accent`, roles of the same names, `DECORATION` contrast class) and `annotation-kind-text:<id>:<n>` Text primitives (roles `annotation-kind-label` and `annotation-kind-secondary`, `STATE_TEXT` class with a required `contrastTreatment`), all in the annotations slot with paint order 400 for the shapes (emitted after the box) and 401 for the text. Scene replaces only the fill of the bar and accent with the colour of the annotation's kind, keyed by the annotation id; opacity, order and geometry stay Layout's and the role's. The kind stamp is one `Symbol` primitive per glyph part, `annotation-kind-stamp:<id>:part<n>` (purpose and role `annotation-kind-stamp`, `DECORATION` class), emitted after the box, with the glyph's own paint mode; Scene replaces the fill of a fill part and the stroke of a stroke part with the kind colour. The parts of one stamp are one ink: the contrast gate never takes a sibling part as the ground of a part, and judges each part against the box, bar or canvas under the glyph. The header text has no same-pair rule like note prose: its ground is the topmost prior opaque Rect or Symbol under its sample point, which is the bar, or the note box when the Theme draws no bar.

The optional separate kind heading (#1191) is the Layout-completed Text `annotation-heading:<id>` with purpose/role `annotation-heading`, semantic `annotationHeading`, STATE_TEXT contrast class and paint order 401. Its baseline follows the completed bar text block; its measured line height precedes the body. The bar's completed bounds include only its label/secondary block, not the separate heading. Scene resolves its own role paint and any `colorAlso.header` override without measuring text or choosing coordinates; the contrast gate reads the actual box/artwork ground under it.

Vector artwork behind an annotation (#848, Specification 07) is completed by Layout as one typed `Glyph` shape per layer, placed in declaration order right after the box and emitted by Scene as one `Symbol` per glyph part, `annotation-artwork:<id>:part<n>` for the legacy object or `annotation-artwork:<id>:layer<index>:part<n>` for a list layer (purpose `annotation-artwork`, the selected Theme role, `DECORATION` class), all at paint order 400 (the box's own, not stacked upward like a stamp's parts, which would put them over the text), in glyph order, with the paint box as bounds. The order is therefore box, ordered artwork layers, border, kind frame, text (401 and above). A fill part is painted from the role `fill`, a stroke part from its `stroke` with the glyph's width, cap and join. A tilt rotates the parts with the note. The contrast gate takes a part as ink over the box, never as a host by bounds, and a label takes a part's ink as a ground only where the part's painted area meets the label's bounds (Specification 46 section 8). The omission ladder is Scene's and reads each completed typed layer's parts and selected role before Symbol projection, never grouping by annotation source or role: where the profile lacks `stroke.line-cap` and `stroke.line-join` and a layer has a stroked part, `artworkFidelity` `required` is `E_VISUAL_CAPABILITY_UNSUPPORTED` and `decorative-optional` removes **all** the affected layer's parts, independently of other layers and reports `I_VISUAL_TREATMENT_OMITTED:role=<selected role>;treatment=annotation-artwork;...`, using the existing omission identity and retaining the legacy object's diagnostics; the box and the text are Layout's and are identical with and without the artwork. SVG draws the parts as paths and PNG derives from it. Typst rejects every artwork part with `E_VISUAL_CAPABILITY_UNSUPPORTED` (as for any `Symbol`), so only an omitted artwork compiles there; TikZ draws a fill part as a filled path and fails closed on a stroke-only part (`E_PRESENTATION_PAINT_INVALID`, the adapter has no stroke route for a `Symbol`); no adapter is changed by this feature and PDF is derived from SVG and not verified separately.

A tilted annotation (#584 A584-3, Specification 07) is completed by Layout: the box, title bar and accent are closed `Symbol` polygons (a balloon already is one) whose bounds are the axis-aligned bounds of the rotated rectangle, the stamp's glyph parts keep their paint with rotated points, and each text is a `Text` whose `textLayout.orientation` is `tilt` with a non-zero `rotationDegrees` of at most 15 (clockwise, about the baseline start `baseline`), its `bounds` the rotated bounding box. `scene-v0.7` widens `textLayout.orientation` and `rotationDegrees` in place and `scene_document` writes a document that carries a tilt as v0.7; Scene v0.6 is not edited. The contrast gate takes the sample point of a rotated text at the centre of its bounds, which lies inside the rotated box, so the same ground rules judge it. The perceptibility text-intersection check does not compare two tilted text runs of one source: the stacked lines of a rigid note never overlap, though their axis-aligned bounds can. SVG rotates a text about its baseline start (`rotate(angle x y)`) and draws the polygons as paths; TikZ rotates a `base west` node about the same point; Typst rejects the `Symbol` box with `E_VISUAL_CAPABILITY_UNSUPPORTED`, as it already does for a balloon, so no unverified Typst pivot is shipped.

A small-caps text (#1285, Specification 07) is a `Text` whose `textLayout.textTransform` is `small-caps` and whose `runs` hold, per line, the measured runs in order: each run is capitals with its own `fontSize` and `inlineSize`, the runs of a line join to that line, and the line's inline size is the sum of the run sizes plus the letter spacing between runs. A Scene with runs is `chrona/scene/v0.7`. An adapter draws each run at its size and synthesizes nothing.

A compressed text (#585 I585-1, Specification 07) is a `Text` whose `textLayout.horizontalScale` is a number from 0.5 up to but excluding 1, written only when the role declares one; its `bounds` already carry the compressed width. `scene-v0.7` gains the optional property in place and `scene_document` writes a document that carries one as v0.7; Scene v0.6 is not edited. SVG, and PNG through resvg, write `transform="[rotate(angle x y) ]matrix(s 0 0 1 x(1-s) 0)"`: the scale acts about the baseline start in the text's own frame, before any rotation. Measured: resvg gives an ink width of exactly `s` times the natural width with the left edge fixed, also under a rotation. Typst writes `#scale(x: s%, y: 100%, origin: left + top, reflow: false)` inside the `#rotate`; that fragment measures the same ink ratio on Typst 0.15, but the surrounding `#place(left:, top:)` emission is not accepted by that Typst, so no compiled Typst result is claimed. TikZ rejects a compressed text with `E_VISUAL_CAPABILITY_UNSUPPORTED` (no engine verifies a node scale about the baseline pivot). PDF is derived from the SVG and is not image-verified. The contrast and perceptibility gates judge the compressed text by its role and bounds like any other.

A vertical group label (#585 I585-2, Specification 07) uses no new Scene vocabulary: Layout completes every segment as its own `Text` primitive `group-tag:<group id>:<n>` with purpose `group-header`: an upright character is orientation `horizontal` (rotation 0) with bounds of its one-em cell, a sideways run is orientation `rotate-cw` (rotation 90) with the bounds of its quarter-turned line box. The bounds of one label tile its column without overlap, so the perceptibility checks (slot escape, occlusion, text intersection) judge each segment as they judge any text. SVG, PNG through resvg, PDF from the SVG, Typst and TikZ draw it as they draw any horizontal or quarter-turn Text; no adapter shapes vertical text. (resvg does lay out `writing-mode: vertical-rl` natively, but its extents come from shaping that Layout cannot know before painting, and the other adapters have no equivalent, so it is not used.) Group-header text is not a classified state text, so no contrast floor applies to it, horizontal or vertical; the paint-contrast observation `I_SCENE_PAINT_CONTRAST` is listed for every segment.

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
the `rowRule` semantic's `row-rule` Theme role (#1270), group separators use `groupSeparator`, and dependency/explanatory paths use
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

An emitted plot member name with a completed own mark carries that exact
mark's `hostPlacementId` in Scene, not the nearest unrelated mark. Layout
measures the two-dimensional nearest-perimeter distance from completed Text
bounds to that mark on both start and end sides. A candidate farther than two
Text font sizes is rejected before the next declared candidate. Lane `fill`
search may use only the preferred position and one adjacent measured stagger
level within the owning lane; non-lane mode retains its finite side-neighborhood
search. Suppressible exhaustion records its source-keyed suppression; a
required or visible-overflow name with an own mark instead fails with
`E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE`. Scene and adapters never remeasure,
move, or connect the name. No member-label leader Path is emitted (#554).

For the `table-timeline`, `review`, and `minimal` surface instances, Scene emits the
following I3 core primitive set before any adapter is invoked: resolved heading
`Text` parts only when allocated by the Layout Profile (Spec33), each in its
Layout-completed host; one
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
Review Detail observations use `observation-column-label`, `observation-cell` and
`observation-source` Text purposes with the existing text/header/emphasis paint roles.
Their source references and stable placement IDs retain the declared identities
(Spec28); they do not fabricate primary table row/column references. Scene projects
Layout's completed geometry, typography and identities.
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

Heading payloads are formatted by content normalization from the resolved
View templates and permitted values; Layout completes their coordinates.
Their primitive purposes are `title-text` and `subtitle-text`; both carry a measured `TextLayout`. Their ink role is the explicit
registered `heading` or `subtitle` choice when that role binds `fill`, otherwise `text`
(#1164); this choice changes neither geometry nor typography. The adapter must not format the
Project title, View window, selection count, or subtitle wording. A group surface keeps
its group-derived `visualRole`; the resolved Theme token supplies both color and opacity,
and an adapter serializes both token values without choosing a fallback opacity.

An optional kicker is projected before the title as `kicker-text`, with its
Layout-completed baseline/bounds and `kicker` typography. Its own fill activates
the kicker paint role; otherwise the existing `text` ink rule applies (#1189).
Whole and split heading sources share the canonical `kicker`, `title` and
`subtitle` primitive identities. Heading slots are optional on both timeline and
network surfaces; Scene projects only completed parts and never creates a missing
title host or infers part placement. Layout reports nonempty unallocated copy.

The remaining I3 families are closed as follows.  `table-timeline` owns table frame,
header band, column-label Text, group surface/header, alternating row surface, row
rule, and one measured table-cell Text per selected `(objectId,columnId)`.  A selected
semantic relation owns exactly one `dependency-connector` Path with two Layout-completed
ports. A visible View annotation owns a completed box `Rect` (including a rectangular image-backed container) or balloon `Symbol`, measured `Text`, and its declared completed connector `Path`, if any. A Project annotation selected by stable View reference supplies text and object identity to that View annotation; it is not duplicated in the notes slot. Unselected Project notes still own measured Text in the notes slot. Layout, not Scene, owns all ports and geometry under the [#466 candidate contract](../design/issue-466-candidate-placement-design-2026-09-26.md). A present legend slot owns its swatches, measured labels, and
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
For a successful render, each warning emitted by the CLI MUST also be present
in that render's Scene `diagnostics` with the same stable warning identity
(code and source/placement discriminator); the ordered warning facts are
collected once at the render-result boundary (#554). Informational Scene
diagnostics are distinct from warnings. Draft perceptibility checks inspect
the completed preliminary Scene before their findings are added to the final
diagnostic list, avoiding a diagnostic feedback loop. Typed `fitWarnings`
remain additional detail, not a substitute for the Scene warning record.

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
