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
| `opacity` | `number` | finite `[0, 1]` |
| `strokeWidth` | `number` | finite `> 0` |
| `dash` | `dashPattern` | array of finite `> 0` numbers; empty means solid |

The schema validates the structural value shape; `ThemeTokenView` validates the
numeric domain and reports the role-property path. No global width, dash, or
opacity default exists. The semantic paint-channel contract below states when a
role must declare each channel.

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
