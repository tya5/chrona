# Issue 384 — Completed Mark Geometry Design

**Status:** accepted for implementation  
**Issue:** #384  
**Date:** 2026-09-25

## 1. Decision

Chrona Theme is the sole authored owner of finite marker, pattern, and point
symbol treatment.  Scene resolves that authored treatment into adapter-neutral
geometry before invoking an adapter.  An adapter serializes completed geometry
and may neither select an outline by name nor supply dimensions, pitch, angle,
or a fallback shape.

This replaces the scalar Theme v0.6 `marker` and `pattern` values, the
`ScenePrimitive.shape`/`pattern` strings, and the SVG-specific triangle,
diamond, and diagonal-hatch branches.  It intentionally does not publish Scene
serialization (#385), create a general path language, or add the dot-grid
policy requested by #383.

## 2. Ownership and flow

| Layer | Owns | Does not own |
|---|---|---|
| Theme | finite treatment choice and dimensions | SVG/XML, selected objects, coordinates, routes |
| Semantic registry | the semantic role that consumes a treatment | a geometry literal or Theme token identifier |
| Layout | mark bounds and relation route/ports | marker/symbol outline selection or pattern pitch |
| Scene | immutable completed marker, pattern and symbol geometry | authoring policy, measurement, routing, target syntax |
| Adapter | target syntax for completed geometry and capability assertion | geometry selection, defaulting, semantic interpretation |

```text
Theme token + semantic Theme role
        │ finite typed authored data
        ▼
ThemeTokenView / Scene completion
        │ completed path, tile, dimensions and paint
        ▼
ScenePrimitive
        │ target-capability check
        ▼
SVG / PNG / PDF serialization
```

The Color Scheme continues to resolve paint colours.  A marker or pattern never
contains a colour; its paint remains the `ScenePaint` on the same primitive.

## 3. Successor Theme contract

Theme v0.7 replaces v0.6 as the only current runtime Theme contract.  It adds
one `symbol` token kind and changes `marker` and `pattern` values from scalar
names to closed structured values.  Every live Theme resource migrates in the
same implementation slice.  Earlier schemas remain schema-inventory history,
not runtime readers.

### 3.1 Marker

```yaml
dependency-marker:
  type: marker
  value:
    shape: triangle
    headLength: 10
    headWidth: 10
    attachmentOffset: 1
```

`shape` is one of `triangle`, `open-triangle`, or `chevron`.  `headLength` and
`headWidth` are positive finite logical units; `attachmentOffset` is finite,
non-negative, and no greater than `headLength`.  The finite shape catalogue is
implemented in Scene code, never in an adapter.  It expands the shape into a
closed local `PathCommand` outline whose coordinate box is
`[0, headLength] × [0, headWidth]`; the attachment point is
`(headLength - attachmentOffset, headWidth / 2)`.

The resulting Scene payload is:

```text
MarkerGeometry(
  outline: tuple[PathCommand, ...],
  head_length: float,
  head_width: float,
  attachment_offset: float,
)
```

The outline is complete, including an explicit final line back to its first
point when closed.  It contains no SVG `viewBox`, `refX`, marker ID, or fill
syntax.  `open-triangle` and `chevron` use stroke geometry; triangle uses fill
geometry.  That fill/stroke disposition is an immutable member of the geometry
payload, so a renderer does not infer it from a Theme name.

### 3.2 Pattern

```yaml
missing-actual-pattern:
  type: pattern
  value:
    kind: diagonal-hatch
    tileInlineSize: 6
    tileBlockSize: 6
    angle: 45
    strokeWidth: 1
```

The finite variants are:

* `{kind: outline}` — completed as no pattern payload and an outline paint
  family (no fill, required stroke);
* `diagonal-hatch` with positive finite tile sizes and stroke width and an
  angle in `[0, 360)` — completed as a tile/stroke payload.

The completed payload is:

```text
PatternGeometry(
  tile_inline_size: float,
  tile_block_size: float,
  angle_degrees: float,
  strokes: tuple[PatternStroke, ...],
)
PatternStroke(start: tuple[float, float], end: tuple[float, float], width: float)
```

For the initial hatch, `strokes` contains a single unrotated vertical tile
stroke; `angle_degrees` is its completed geometric rotation.  SVG may encode
that rotation with `patternTransform`, whereas another capable adapter may
apply the same affine geometry by its own target syntax.  Neither adapter may
choose a default pitch, angle, or width.  A pattern payload is present only for
the hatch; an outline Rect has its completed no-fill paint and no `pattern`
name to interpret.

### 3.3 Point symbol

```yaml
milestone-symbol:
  type: symbol
  value: {shape: diamond}
```

`shape` is one of `diamond`, `circle`, `square`, and `chevron`.  The Theme role
is `milestoneSymbol`.  The existing semantic bindings (`planned`, `actual`,
and `snapshot`) remain the source of purpose and visual role; their point-mark
projection asks the resolved Theme for `milestoneSymbol`.  No Scene builder
site writes `diamond`.

The Scene maps the finite shape and the Layout-provided mark bounds to:

```text
SymbolGeometry(outline: tuple[PathCommand, ...])
```

with final absolute Scene coordinates.  Square and diamond are closed line
outlines.  Circle and chevron use the existing renderer-neutral line/quadratic
path-command vocabulary.  The adapter serializes that outline as a filled and
stroked path; it does not branch on symbol shape.

## 4. Scene model and completion rules

`ScenePrimitive` replaces `shape: str | None` and `pattern: str | None` with
three mutually scoped optional members:

* `marker: MarkerGeometry | None`, valid only on `Path`;
* `pattern: PatternGeometry | None`, valid only on `Rect`;
* `symbol: SymbolGeometry | None`, valid only on `Symbol`.

The primitive validator rejects a payload on an incompatible kind, a `Path`
whose marker has incomplete paint, and a `Symbol` without its completed outline.
The existing `path_commands` remain the main line route payload; they are not
overloaded as an implicit marker or symbol selection.

`ThemeTokenView` receives typed `marker_geometry`, `pattern_treatment`, and
`symbol_shape` accessors.  It validates structural ranges and finite shape
values even for unit-built resolved Themes.  Resource-schema validation catches
the same authored errors at their Theme source path.  The completion path is:

1. resolve pattern treatment before `ScenePaint`, choosing solid, outline, or
   hatch paint family;
2. resolve `ScenePaint` as today, including Scheme colours;
3. attach completed `PatternGeometry` to a hatch Rect;
4. attach completed `MarkerGeometry` to dependency Paths;
5. expand point-symbol shape against already completed Layout bounds and attach
   `SymbolGeometry`.

This is a Scene operation, not a Layout operation: it selects appearance but
does not alter bounds, routes, text placement, or layout feasibility.

## 5. Capability contract

Three required visual capabilities are introduced:

* `mark.marker-geometry`;
* `paint.pattern-geometry`;
* `mark.symbol-outline`.

The `validate_surface_visual_profile` gate derives required capabilities from
the completed primitive members, before renderer invocation.  The SVG, PNG,
and PDF profiles advertise all three: PNG and PDF intentionally inherit SVG
serialization before raster/PDF conversion, so they consume precisely the
same completed Scene geometry.

The direct experimental Typst and TikZ adapters must call the same capability
assertion using their declared adapter support.  TikZ may implement the
completed outlines/tile geometry; Typst is allowed initially to reject a
surface requiring an unsupported capability with
`E_VISUAL_CAPABILITY_UNSUPPORTED`.  It must not emit a comment-only Path or a
fill-only Rect while claiming successful rendering.  This resolves the current
silent difference without widening the public render-context target surface.

## 6. Diagnostics and migration

Theme v0.7 schema `oneOf` branches supply the finite accepted values.  Runtime
accessors preserve `E_THEME_TOKEN_TYPE` for malformed resolved input; the
resource loader reports its ordinary schema diagnostic at the authored token
path.  Capability denial remains `E_VISUAL_CAPABILITY_UNSUPPORTED` and names
the missing completed-geometry capability.

All current Theme resources migrate atomically with their Context source maps,
fixtures, tests, vocabulary policy, and generated vocabulary inventory.  Their
geometry preserves current SVG appearance exactly: triangle 10×10 with a one
unit attachment offset; diagonal hatch 6×6 at 45° with a one-unit stroke;
diamond point marks.  The implementation adds focused non-default fixtures for
different marker dimensions, hatch pitch/angle, and at least one non-diamond
symbol.

## 7. Non-goals

* Arbitrary author-supplied SVG, raw path strings, target-specific markup, or
  user-defined geometry catalogues.
* Dot-grid, stipple, gradients, or any #383 editorial policy.
* A serialized `scene-v0.1` document, external Scene adapter, or Scene
  stability promise (#385).
* The two semantic-registry literal repairs identified by #385.
* A change to Layout mark bounds, relation routing, semantic selection, or
  public materializer byte policy other than regenerated evidence required by
  this contract migration.
