# Completed Scene Paint

**Status:** Design complete — #332 implementation pending.  
**Owns:** the typed, renderer-neutral paint value carried by a completed Scene
and the one-way conversion from resolved Theme/Scheme policy.

## 1. Authority and boundary

Theme and Color Scheme remain the only authoring authorities for appearance.
After closure resolution, Scene converts a selected semantic role into a
`ScenePaint`; a renderer receives that completed value and no Theme token view.
`visualRole` remains Scene provenance and inspection metadata, not a lookup key
for an adapter.

This does not restore the removed `ScenePrimitive.color` escape hatch. A
`ScenePaint` is derived internally from a validated resolved Theme only, is
immutable, and cannot be supplied by Project, View, Layout, or an adapter.

## 2. Typed value

Every primitive has exactly one `ScenePaint`:

```text
ScenePaint {
  fill: Color | absent
  stroke: Color | absent
  strokeWidth: positive finite SceneUnit | absent
  dash: finite sequence of positive finite SceneUnit lengths
  opacity: finite number in [0, 1]
}
```

`dash: []` is solid. A stroke is required when `strokeWidth` or a non-empty
`dash` is present; a stroke requires `strokeWidth`; fill and stroke may coexist.
At least one of fill or stroke is required. All checks happen before a
`SceneSurface` exists and fail with `E_PRESENTATION_PAINT_INVALID` rather than
being repaired by a renderer.

`SceneSurface` also carries its resolved canvas `ScenePaint`. Consequently the
canvas background cannot be re-read from `background.fill` by an adapter.

## 3. Theme contract and resolution

Theme v0.3 continues to use `colorBindings` for `role.fill` and `role.stroke`.
Its non-colour `roles` vocabulary gains these bindings:

| Binding | Value token | Validity |
| --- | --- | --- |
| `opacity` | optional `number` | finite `[0, 1]`; absence completes to `1.0` in `ScenePaintResolver` |
| `strokeWidth` | `number` | finite `> 0` |
| `dash` | `dashPattern` | array of finite `> 0` numbers; empty means solid |

The schema validates the structural value shape; `ThemeTokenView` validates the
numeric domain and reports the role-property path. No global width or dash
default exists. The resolver's closed role contract, rather than an adapter,
completes absent opacity to explicit `1.0`. The semantic paint-channel contract
below states when a role must declare each channel.

`ScenePaintResolver` is the only conversion point. It accepts a semantic
binding, its selected concrete role (including deliberate variants such as
`variance-behind` and category legend roles), and the resolved Theme. It returns
completed paint or a stable pre-render diagnostic. Layout is not an input.

## 4. Channel contract

| Primitive family | Required channels | Permitted channels |
| --- | --- | --- |
| Text | fill | fill, opacity |
| Solid Rect / Symbol | fill | fill, stroke, strokeWidth, dash, opacity |
| Outline Rect / Symbol | stroke, strokeWidth | fill, stroke, strokeWidth, dash, opacity |
| Hatch Rect / Symbol | stroke, strokeWidth | fill, stroke, strokeWidth, dash, opacity |
| Path / connector / rule | stroke, strokeWidth | stroke, strokeWidth, dash, opacity |
| Canvas | fill | fill, opacity |

The selected pattern is completed Scene form metadata, not renderer policy. It
does not change channel requirements. A mixed fill/stroke mark carries both
channels explicitly. Pattern geometry (for example hatch spacing) must be a
completed renderer-neutral form parameter if introduced later; #332 does not
retain SVG's hard-coded hatch width as an implicit policy.

Semantic registry entries identify the primitive family, so coverage is closed:
comparison marks, group/calendar/axis decorations, table and legend swatches,
annotation boxes, summary bars, network nodes, rules, dependencies, annotation
leaders, and all text families are resolved through the same resolver. A dynamic
category role is resolved before this point and is equally subject to the contract.

## 5. Adapter contract

SVG serializes `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, and
`opacity` directly from completed paint. TikZ serializes the equivalent completed
properties. A target that cannot express a completed paint/pattern combination
rejects it with `E_PRESENTATION_PAINT_UNSUPPORTED:<target>` before writing an
artifact. It must not omit a channel, turn a dash solid, or select a fallback.

For SVG drawable shapes, an absent completed fill serializes as explicit
`fill="none"`; omitting the attribute would invoke SVG's initial black fill
and contradict the Scene value. A completed pattern or gradient uses one
explicit target fill reference. ClipPath-only geometry is structural, not a
painted primitive. The PNG route inherits this mapping through its SVG input.

The public renderer boundary is `SceneSurface + viewport`; it no longer accepts
`ThemeTokenView`. Output byte checks prove that changing a resolved Scene paint
changes only declared target attributes, and a search gate rejects Theme/Scheme
imports from renderer modules.

## 6. Invariants and migration

1. Identical closure inputs produce byte-identical completed Scene paint.
2. A Scheme change can change completed color values, but not selected facts,
   geometry, primitive identities, or paint-channel requirements.
3. Scene has no unresolved Theme token IDs or renderer-specific paint strings.
4. Renderers read no Theme/Scheme resource and make no paint decision.
5. Missing or invalid channels fail before artifact creation.

This is an intentional clean-boundary migration. Callers constructing old
role-only `ScenePrimitive` values must migrate; no adapter preserves the
incomplete contract.

## 7. Layout-only visible stroke extents after lane membership (#467)

For post-membership label obstacles and all final mark/icon placement, Layout
derives geometry-only visible extents from validated resolved Theme geometry
metrics and normalized icon closure. This does not make Layout a paint
resolver. `ScenePaintResolver` remains the sole conversion of Theme/Scheme
paint policy into completed `ScenePaint`; Layout MUST NOT resolve color, paint
family, opacity, dash, gradient, shadow, or a replacement stroke style, and
it MUST NOT construct or pass `ScenePaint` as a membership input.

The post-membership geometry footprint uses the same concrete mark role, selected glyph
variant, Theme geometry metrics, temporal scale, and icon stroke scale as final
Layout/Scene composition. An `ObstacleSegment` stores its unexpanded
centerline and stroke width; an `ObstacleRect` stores already expanded
visible bounds. Stroke and collision clearance remain separate. A primitive's
visible stroke is represented exactly once, and an implementation MUST test
that segment and rectangle paths do not double-expand or omit it.

Rectangles expand by half their resolved stroke width on each side. Segment
geometry carries its stroke width and the obstacle collision machinery
accounts for its extent. A path represented by a conservative control-point
envelope expands that envelope by ten times its stroke width on every side.
This target-independent bound accommodates admitted miter limits up to ten
without changing adapter output or adding Scene paint policy. Because
`ScenePaint` has no miter-limit member, Layout cannot set renderer paint
policy to make the footprint fit. The bound may affect later label and route
placement, but MUST NOT change the data-only lane membership (Spec 38).

Layout returns completed point-symbol and icon path geometry before Scene
construction. This includes Theme-selected built-in shape geometry, Theme
glyph-part paths, point legend swatches, and normalized vector icon paths
transformed into their placed viewport with per-path stroke widths scaled
once. Theme glyphs retain contain-center fitting, `paint: none` omission,
part order/IDs, the built-in diamond outline override rule, and deterministic
path closure/arithmetic. Vector icons retain normalized path commands and
asset cap/join. Raster icons reserve the complete placed viewport, without
alpha-based geometry inference. Theme color/Scheme changes alone cannot
affect these footprints; changes to geometry-bearing Theme metrics or
normalized icon assets may.
In lane mode, per-path vector collision facets carry a typed common icon
emission group and the exact per-path paint/cap/join/already-scaled stroke
facts. B2 groups them by completed placement identity and projects one Scene
ICON with paths in declared order. Raster icon facets retain the exact asset
identity, viewport and bytes. Neither B2 nor Scene may reload an icon asset,
retransform paths, or rescale its stroke. See the [S2b icon emission
correction](../design/issue-467-b1b2-s2b-icon-emission-closure-correction-2026-09-27.md).
The expected-emission inventory fixes icon cardinality before Scene projection:
vector path indices are unique, contiguous and complete against one declared
path count, all common group metadata agree, and exactly one Scene ICON is
emitted per completed icon placement. Stroke paths require a finite completed
width; commands and bounds must agree with the completed viewport/footprint.
An absent or extra path/ICON is a closed-plan failure, not a reason to reload
or infer icon data at projection time. See the [S2b closure correction](../design/issue-467-b1b2-s2b-closure-reconciliation-correction-2026-09-27.md).

The Scene builder receives those completed path values and does not resolve
Theme symbol variants, construct glyph outlines, transform normalized icon
commands, or scale icon strokes. It supplies each completed primitive/path's
typed paint intent to `ScenePaintResolver`, which returns completed paint.
That resolver is the only location permitted to convert glyph-part or
icon-path fill/stroke modes and authored colors into `ScenePaint`; a helper
MUST NOT modify a `ScenePaint` after resolution. This keeps paint conversion
after geometry without giving Scene a second geometry or paint authority.
Implementations characterize existing automatic/explicit Scene/SVG bytes,
point legend swatches, and material-icon SVG/materializer outputs across this
move before acceptance.

These are Layout extents only. Scene still resolves paint after geometry is
complete, and SVG/PNG/TikZ adapters still serialize or reject the completed
Scene value according to this specification. No renderer may repair or
reinterpret a completed obstacle, and no obstacle may feed back into lane
membership.

## 8. Completed contrast evidence (#459)

For finite classified text, decoration and data-mark roles, contrast is
measured against the topmost earlier opaque, flat-filled Rect covering the
primitive's painted sample point; if none covers it, the opaque canvas is
the ground. The finding records the ground primitive identity or `canvas`,
ground colour, evaluated paint channel and ratio. A classified mark has a
3.0:1 visibility floor; a required state-text role has a 4.5:1 floor.
`variance-behind` is always required. A translucent or non-flat overlapping
host cannot be treated as an opaque ground by assumption. The evaluator is a
Scene observer, not a Theme or adapter paint selector. This supersedes the
canvas-only ground rule of the initial #431 design.

A stroke-only Rect is sampled at its painted left-edge midpoint rather than
the unpainted bounds centre; the exact sample coordinate is part of the
finding. A hosted progress-fill is independently tested against its earlier
host and is not exempt from the mark floor. See the #459 painted-sample
correction for the finite geometry rule.

An earlier opaque linear-gradient Rect is also a valid ground. Its completed
absolute gradient is sampled at the same point by clamped sRGB stop
interpolation; the finding identifies a `gradient-sample` ground. This
supersedes the first #459 design's exclusion of all gradient hosts. Other
non-flat or non-opaque hosts still require an explicit contract.

A dual-channel Rect or Symbol is evaluated at a separate painted sample for
each channel: fill at bounds centre, stroke at the left-edge block midpoint.
Either channel may carry a data mark's 3.0:1 visibility floor, and the
finding records the winning channel and its own ground. Theme-supplied mark
outlines may therefore preserve a category-coloured fill when the same
category also colours its background. No outline is inferred by Scene or an
adapter (#459).
