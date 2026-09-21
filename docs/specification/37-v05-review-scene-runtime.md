# v0.5 Review Scene Runtime

**Status:** Proposed — M27 migration design
**Depends on:** Specifications 08, 24, 30, 33, 36 and ADR-0028.
**Owns:** the derived v0.5 Scene token view and the generic construction of a completed
Review `SceneSurface` from current resource contracts.

## 1. Input closure

The runtime accepts only these already-resolved inputs:

1. `ReviewProjection` and normalized `SurfaceContentInput`;
2. the v0.5 Render Context's resolved Theme v0.2 and Color Scheme result;
3. the resolved Layout Profile v0.2 and immutable Layout Manifest;
4. declared font metrics and the immutable `MeasuredSources` result; and
5. target capabilities.

It MUST NOT read a legacy settings document, a legacy serializer configuration, a
profile ID, a project/example ID, a host font, or an implicit renderer default. The
derived token view and Scene are non-persistent; their identity is the input closure
identity plus a runtime version, not an authoring resource.

## 2. Derived ThemeTokenView

`ThemeTokenView` is the typed resolution boundary between Theme v0.2 and Scene/SVG. It
dereferences every required role property through `resolvedTheme.body.roles` and
`resolvedTheme.body.values`, validates the declared token type, and exposes only:

| Need | Current source | Failure |
|---|---|---|
| Font family/weight/size/line height | role `fontFamily` / `fontWeight` / `fontSize` / `lineHeight` token | `E_THEME_ROLE_REQUIRED` |
| Fill/stroke | color-bound role `fill` / `stroke` token | `E_THEME_ROLE_REQUIRED` |
| Opacity | role `opacity` number token, otherwise explicit `1` only when the role contract declares opacity optional | `E_THEME_ROLE_REQUIRED` |
| Marker/pattern | role `marker` / `pattern` token | `E_THEME_ROLE_REQUIRED` |
| Numeric geometry | named Theme metric token | `E_LAYOUT_METRIC_REQUIRED` or `E_LAYOUT_TOKEN_TYPE` |
| Text alternative | role `textAlternative` token | `E_THEME_ROLE_REQUIRED` |

The view does not reintroduce `paints`, `strokes`, a Theme v0.1/v0.2 compatibility
object, or global default values. Scene primitives carry their resolved role and
completed geometry; SVG receives the token view plus primitives and may only format
attributes.

### 2.1 Role typography and marker contract

Theme v0.2 roles may bind `fontSize` and `lineHeight` to declared `number` values in
addition to `fontFamily` and `fontWeight`. The builder selects the role named by the
primitive family (`heading`, `axis`, `legend`, `summary`, `annotation`, or `text`);
the selected role must bind all four typography properties. A Theme may deliberately
bind several roles to the same values, but the Scene never substitutes a renderer
default or a body metric for a missing role binding. `TextLayout` stores the resolved
size, family, and weight so SVG serializes rather than infers typography.

The existing named metrics remain layout inputs only. `text.body.size` and
`text.body.lineHeight` determine minimum content geometry where the Layout contract
requires them; they are not a fallback typography contract.

A dependency Path whose selected Theme role binds `marker` carries that declared
marker token in `ScenePrimitive.shape`. The SVG adapter emits a definition only for
referenced declared markers and attaches it only to the completed path endpoint.

### 2.2 Annotation anchor and leader contract

The Scene supports the existing View annotation contract for object anchors only:
`anchor.kind: object` together with `id`, `facet`, and `endpoint`. It resolves that
reference against projected planned/Actual marks through the existing annotation
resolver. An absent projected mark, absent Actual, unsupported anchor kind, or
incomplete anchor diagnoses before SVG; it never falls back to an object row or a
free coordinate.

The resolved mark endpoint is mapped through the completed timeline scale and row
bounds. The measured annotation box is placed within its resolved `annotations` slot
using its declared side/alignment and that slot's manifest overflow policy. For
callout, note, and explanatory-arrow purposes, a deterministic bounded orthogonal
leader runs from the resolved anchor to the nearest annotation-box port, avoiding
completed row and annotation bounds. The leader's `source_ref`, endpoint port IDs,
and `annotation` role are retained on the Path. `highlight` has no leader. This is
derived geometry only: neither annotations nor relations may introduce authored
coordinates or an alternative layout resource.

## 3. Scene construction sequence

The builder executes this bounded sequence:

1. validate target capabilities and resolve `ThemeTokenView`;
2. convert each Layout Manifest slot to `SceneSlot`; require title/table/timeline/axis;
3. derive group and row bounds from the resolved timeline/table slots, ordered View
   Review rows, measured row minimum times bounded member count, and declared Layout
   overflow policy; assign member subtracks only after row bounds are complete;
4. derive calendar axis intervals using existing `layout.axis` functions and the
   versioned ISO fit rule below; measure labels before creating axis primitives;
5. create table cells from `SurfaceContentInput.table_cells`, marks from
   `ReviewProjection`, and all conditional Actual/variance/missing-Actual families;
6. create optional families only from present normalized content and matching slots;
7. route selected relations/annotations with the existing finite router; and
8. validate source provenance, text layouts, bounds, required slot-family completion,
   and deterministic z-order before producing `SceneSurface`.

Rows, groups, and ordered Review Items are derived from View projection order. They
never become Layout authoring state. Axis/mark coordinates are derived only from the completed timeline
slot and half-open View window. A required label or panel that does not fit diagnoses;
it is never silently omitted, clipped, or replaced by a fixed 28-day cadence.

The builder consumes `MeasuredSources.measurements` and `.metric_values` verbatim. It
does not recompute Theme metrics or text measurement during composition; a missing
measurement boundary diagnoses `E_PRESENTATION_MEASUREMENTS_REQUIRED`.

### 3.1 ISO axis fit rule

Current resource contracts contain no axis locale, formatting preset, or fixed
calendar-level declaration. The v0.5 Scene runtime evaluates `year`, `quarter`,
`month`, `week`, then `day` using `AxisInterval.label`; it selects the most detailed
candidate for which every FontMetrics-measured label fits its interval and adjacent
labels do not overlap. If none fits, it fails with `E_PRESENTATION_AXIS_OVERFLOW`.
This generic versioned rule is Scene semantics, not an adapter default or a new
authoring resource.

### 3.2 Optional content normalization

`SurfaceContentInput` is produced by a current-resource normalizer over the Projection,
Project, View, and any resolved current detail/summary profile. The normalizer does not
accept the deleted Settings shape. It includes an optional family only when both the
selected source and its declared Layout source exist; a missing required source is a
diagnostic, while an absent optional family produces no primitive.

Detail Profile source validation derives source presence and required/optional policy
from the immutable Layout Manifest. It does not inspect an authoring-layout/settings
object or reconstruct slot declarations.

Each slot decision carries its resolved `priority` and `overflow` policy verbatim; a
manifest without those fields is incomplete for v0.5 optional-family composition.

## 4. SVG adapter migration

The v0.5 adapter consumes `SceneSurface` and `ThemeTokenView`. It maps primitive kinds
and completed token values to SVG attributes, emits definitions for only referenced
markers/patterns, validates every required primitive bounds, and retains scene ID,
source reference, semantic facet, visual role, and accessibility text. It does not
inspect View, Layout, Detail, Summary, Project, or raw Theme documents.

The old `scene_svg` implementation is retired rather than made conditional. Its
role-to-legacy-paint maps are replaced by token-view lookups; its direct `theme[paints]`
and `theme[strokes]` access is prohibited.

An SVG-capable Theme binds every selected primitive role directly. Required core
bindings are `background`, `text`, `table-header`, `axis-major`, `planned`, `actual`,
`missing-actual`, `variance-ahead`, `variance-on-track`, `variance-behind`, and
`dependency`; annotation bindings are required only when annotations are selected.
There is no role-to-color fallback map.

Selected text roles bind `fontFamily`, `fontWeight`, `fontSize`, and `lineHeight`.
Selected dependency roles bind `stroke` and `marker`; selected annotation roles bind
`fill` and `stroke`, while annotation text uses the selected `annotation` typography
role. A missing selected binding diagnoses at the token boundary.

## 5. Migration and acceptance

No serialized migration is required: old settings and old Scene artifacts were not
user input contracts after M24. M27 creates new derived output from the same current
authoring resources. Fixtures must prove a missing token, missing required slot,
 invalid font metric, axis collision, incomplete annotation anchor/route, and missing optional content policy all diagnose
before SVG output. A complete fixture proves deterministic output and no source-ID
branch.
