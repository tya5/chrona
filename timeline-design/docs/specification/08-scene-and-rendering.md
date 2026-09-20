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

### 3.3 Resolved presentation input and identity boundary

The Scene Builder receives one immutable **ResolvedPresentationInput**.  It is derived
once by the coordinator from the View Projection, resolved Style/Theme, Detail,
Layout, Render Context, and target capability declaration.  It contains semantic
facets, visual roles, selected slot instances, measured text inputs, resolved
layout/routing policy, and the resolved logical bounds for every surface slot, row,
and derived lane track; it is not another persisted authoring resource.  A slot bound
is Scene input, not an adapter convention.

Each temporal or annotation projection has a `projectionInstanceId` composed from the
stable slot ID, source reference, semantic facet, and declared primitive purpose.  A
visual role may change paint or glyph choice, but MUST NOT rename or replace the
semantic facet.  Thus a planned mark drawn as a baseline remains `planned`, and an
Actual point remains `actual` even when they share geometry or paint.  `sceneId` is
derived from `projectionInstanceId` plus the primitive-purpose suffix.  Array order,
coordinates, renderer element IDs, and display text are not identity inputs.

The Builder alone converts this input into measured geometry, ports, obstacles,
track bounds, and primitives.  An adapter receives neither authoring resources nor a
semantic View Projection and MUST NOT recreate a scale, select a slot, choose an
anchor, measure text, assign a lane, calculate a row/track y coordinate, or resolve a route.

## 4. Coordinate system and temporal scale

### 4.0 v0.1 Scene profile

A Scene profile declares layout policy, not geometry. The first Date-only profile is
intentionally closed so renderer adapters cannot silently choose a scale or routing
algorithm:

```yaml
version: chrona/presentation/v0.1
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

The scale domain, output range, origin, and unit ratio MUST be recorded in the Scene manifest. Human-facing inclusive-end labels remain a renderer or View presentation choice; they do not change the half-open geometry rule above.

Non-linear working-day compression, DateTime scales, discontinuous intervals, and zoom-dependent semantic aggregation require named future Scene profiles. They MUST NOT be inferred from a calendar or a renderer's axis widget.

### 4.3 Lanes and ordering

The View supplies lane membership and deterministic order. Scene assigns each lane a concrete extent and each item a concrete position within that extent under the declared layout profile. Lane geometry is presentation geometry, not Project containment.

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
| `Group` | Ordered containment, transform, clipping, and shared metadata |
| `Rect` | Span bars, bands, lane backgrounds, and callout boxes |
| `Symbol` | Point events, markers, and reusable semantic glyphs |
| `Path` | Dependency connectors, explanatory arrows, variance marks, and leaders |
| `Text` | Labels, notes, axis labels, and accessible text alternatives |
| `Clip` | Explicit viewport or group clipping region |

Primitives contain geometry, token references, and metadata; they do not contain scheduling rules. A Scene profile may define a composite convention such as “planned span = `Rect` plus `Text`”, but renderers must not invent that convention independently.

## 6. Projection rules

Scene construction follows a deterministic order:

1. validate explicit inputs and resolve the temporal scale, viewport, and lane geometry;
2. project planned, baseline, and actual temporal placements to primitive geometry;
3. emit labels and accessible alternatives using the declared layout metrics;
4. project semantic dependencies with dependency-specific connector rules;
5. project explanatory arrows and annotations with their own connector and anchoring rules;
6. resolve declared collision, clipping, and z-order policy; and
7. emit the Scene, manifest, and diagnostics.

The detailed finite algorithm, annotation purpose table, port exception, lane formula,
and route failure classification are owned by specification 30 §7.5. This order is
normative: a renderer must not perform a later placement, remeasurement, lane, or
route pass after Scene emission.

### 6.1 Planned, baseline, and actual geometry

Planned placement, Snapshot placement, and Actual observation may each produce separate primitives for the same stable object. Their source identity remains the same while their primitive purpose and roles differ. The Scene MUST NOT collapse them merely because their geometry coincides.

If a comparison is absent, unmatched, or semantically unknown, the Scene emits only the primitives authorized by the View Projection and the corresponding diagnostic or `variance-unknown` role. It MUST NOT fabricate an actual bar, completion date, or forecast.

### 6.2 Relationships

Semantic dependencies are projected from the selected endpoint placements and retain the `dependency` role. An explanatory arrow is projected from a View-local source and target anchor and retains the `explanatory-arrow` role. They use separate source kinds and must remain distinguishable even when a Theme intentionally gives them similar tokens.

An omitted relation endpoint may terminate at a declared non-rendered boundary only when the View Projection explicitly represents that boundary. Scene must not synthesize a hidden object or relationship to complete a path.

### 6.3 Annotations

The View declares an annotation's stable anchor and logical preference, such as above, below, left, right, or a named lane. Scene resolves concrete offsets, callout bounds, leader paths, and collision adjustments under the Scene profile.

Collision resolution may move a presentation annotation within its declared placement constraints, but must retain its anchor and produce deterministic output. If no legal placement exists, Scene emits a diagnostic and applies the profile's explicit fallback; it must not silently detach the annotation.

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

### 8.3 Future renderers

Canvas, PDF, image, and presentation-file exports are possible targets if they can declare their capability limits. A target that cannot preserve a required distinction must report that loss; it may not erase it without notice.

## 9. Output capability successor

Every adapter target supplies `chrona/output-capability/v0.2` before construction. The
output manifest records its target capability profile, adapter version, evaluation
closure, and all loss diagnostics. SVG is the baseline; PDF, raster, canvas, and
presentation outputs are derived adapters with no authority to alter Scene or Project.
A missing required capability rejects the request; an explicitly permitted loss remains
visible as a stable diagnostic and manifest entry.

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
