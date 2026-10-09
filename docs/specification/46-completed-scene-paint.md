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
supersedes the first #459 design's exclusion of all gradient hosts. A translucent
host is composited over its own ground (#1013, section 8); other non-flat hosts still require an explicit contract.

**Contrast constraints are an opt-in design option (#995, #1126).** The floors of this section (3.0:1 for a
mark, 4.5:1 or 3.0:1 for a state text, 4.5:1 for ground text, 1.10:1 for a decoration) are design constraints a
Theme chooses; they do not bind a Theme that does not ask. Every finding belongs to a *class*, fixed by the
registry's contrast class of the role and never by a slide: `mark`, `stateText`, `groundText` and `decoration`,
plus `unsupportedGround` for a mark or text whose ground cannot be computed (a decoration on such a ground follows
`decoration`: a measurement that cannot be made, not an illegibility). A finding carries `severityClass`
(`legibility` or `decoration`). The Theme's `contrastPolicy` (Specification 07) sets each class `none`,
`warning` or `error`:

- `error` is the blocking finding with the code it always had (`E_SCENE_MARK_CONTRAST`,
  `E_SCENE_STATE_TEXT_CONTRAST`, `E_SCENE_DECORATION_CONTRAST`, `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`). The render
  fails with it, at `/body/contrastPolicy/<member>`, before any adapter output.
- `warning` is the same finding with its warning code (`W_SCENE_MARK_CONTRAST`, `W_SCENE_STATE_TEXT_CONTRAST`,
  `W_SCENE_CONTRAST_GROUND_UNSUPPORTED`, `W_SCENE_DECORATION_CONTRAST`, `W_SCENE_DECORATION_GROUND_UNSUPPORTED`),
  the measured ratio and the floor. It reaches the render's warning records, the Scene `diagnostics`, the CLI and the MCP
  payloads and the corpus contrast report (`Warnings`), and fails neither render, Theme resolution nor the corpus
  gate.
- `none` is an `info` row: the measured ratio stays in the evidence and nothing is reported.

**A Theme that declares nothing is not opted in: every class is `warning`.** The evaluator itself takes the
policy as an argument and, given none, keeps the strict gate (legibility `error`, decoration `warning`) so that the
geometry of every grounded finding is tested unchanged; the Theme default is applied by the render. A floor is
switched, never retuned: a Theme cannot change a number.

The corpus tool reads Scenes only. The repository keeps its own guarantee for the Themes it ships with the registry
`conformance/contrast-opt-in.yaml`: it reads each committed Scene's Theme id from the Scene's provenance and
evaluates a listed Theme with `mark`, `stateText`, `groundText` and `unsupportedGround` at `error` (and
`decoration` at `warning`) and an unlisted Theme with every class at `warning`; the report lists the unlisted Themes
and their warnings. A Theme that declares `error` itself needs no entry, because the render that makes its Scene
fails first. Listing a Theme is the repository's explicit choice; nothing is listed by default.

Never governed by the policy, whatever its value: a malformed paint (`E_SCENE_CONTRAST_PAINT`), an invalid
treatment (`E_SCENE_STATE_TEXT_CONTRAST_TREATMENT`) and a malformed Scene document: they are structural, not
contrast constraints. A mark or text on a translucent host is judged on the host composited over its own ground
(#1013, below) and is `unsupportedGround` only where that composite cannot be read; a mark or text on a faint
decoration is judged on that decoration's colour. Theme resolution checks text only against its own canvas or box
(the Theme's static checks, `E_SCHEME_STATE_TEXT_CONTRAST` and kin) and is not governed either.

**Ground text and pattern grounds (#884, #980).** Free text, ink that lies on a ground
the Theme chose, keeps the shared visual role `text` (and so the Theme `text` ink) or a
role of its own, so its contrast class is resolved from its purpose, never from the role
`text` alone: the class `ground-text` is "free ink on a ground". It covers the group
header (#884) and every other Text a surface draws that no role-classified binding
covers (#980): the as-of label, member labels (outside a bar, and inside it on the mark),
axis labels (every tier), table column labels and cells, group details, the title and
subtitle, legend labels, project notes, relation labels, milestone digest entries,
summary text, the note index, and the callout, highlight and arrow annotation prose. A
label whose role has its own class (a variance cell, note prose, an annotation kind
header, a period label) keeps that class. Resolution is by the role's own binding, else
for a Text primitive by purpose together with the shared role `text` or the role the
purpose's binding declares; a non-Text primitive and an unregistered purpose are never
ground text, and the semantic registry carries a guard that every `label` binding is
classified (or named as classified by role), so a new label purpose cannot reopen the
hole. The treatment is always `required` (4.5:1, paint channel `fill`,
`E_SCENE_STATE_TEXT_CONTRAST`) and is not authored by the Theme: no `contrastTreatment`
and no knob lowers it, and the decoration severity of #995 never softens it. The ground
is the one above, so a group tint, a gradient, a row band, a region-frame fill or a flat
band under the label is read as completed, and a label whose ink is too close to what
lies beneath it is a gate error. A label that carries its own box (a label chip, an
opaque Rect one paint order below it) is judged on that box; a translucent chip or host
is judged on its composited ground (#1013, below). A Rect with a
completed catalogue pattern (Scene v0.7) is ground in two colours, as a canvas
texture is: the substrate is its fill and the ink its stroke, and every
classified text and mark over it, except a decoration, is judged on both, the
worse ratio deciding (`ground_kind` `pattern-host-substrate` or
`pattern-host-ink`; a canvas texture stays `texture-substrate` and
`texture-ink`).

**Transparent surface overprint (#888).** An ink-only `canvas-texture` is not a
host by its bounds. For legibility classes, its actual repeated ink contributes
a composited ground only where it touches the subject bounds; a later opaque
host hides it and a translucent host composites over it. Holes retain the
underlying canvas or host. Opaque texture behaviour is unchanged.

Above-content overlays are evaluated separately from prior-ground lookup.
For each existing backdrop alternative `B`, form subject foreground `F` by
compositing its channel ink/opacity over `B`. Sample a continuous radial overlay
at that channel's existing painted sample (fill centre, stroke left-edge block
midpoint) and composite it over BOTH `F` and `B`. Then the single sparse pattern
overlay adds touched-ink and uncovered alternatives in Scene paint order,
compositing its ink over both members of the covered pair. Evaluate the existing
floor against each resulting pair; opaque overprint that erases contrast fails.
This retains the existing point-sampled gradient and conservative bounds-contact
contracts; it is not a universal every-pixel proof. Do not Cartesian-mix
independent overlay colour lists or treat a later overlay as an earlier host.
Decoration tint retains its dominant-substrate rule; no legibility floor changes.

Periodic stroke contact uses the flattened path's half-width segment bodies,
declared butt/round/square endpoint caps, and bevel/round/miter joins, clipped
to the tile and canvas. Miter contact uses the offset-line intersection within
ten stroke widths of the join; an intersection outside that bound is replaced
by a local disk of that radius as a conservative alternative covering the
admitted miter limits up to ten (section 7). This is an observer envelope, not
an adapter miter-limit setting. It changes no annotation/frame contact rule.

Pattern contact uses completed tile primitives, repeat phase, rotation and clip,
not the full canvas bounds. The sparse-contact path admits fill-less patterns
only: substrate operations require opaque fill and are rejected during paint
completion. Opaque patterns instead retain conservative substrate/ink contrast
using the positive final visible-ink density (Specification 64 section 8).
Overlapping sparse primitives paint the same opaque ink before the layer
opacity is applied once. Circle strokes contact a clipped convex query polygon
when its radial-distance range intersects
`[max(0,radius-width/2), radius+width/2]`. Minimum distance is zero for an
enclosed centre, otherwise the minimum centre-to-edge distance; maximum
distance is attained at a vertex. An ink-filled stroked circle is the outer
disk. This is analytic contact, not density-grid sampling. An unexpected
substrate operation at this observer fails closed. Bound contact work to 4096
candidate tile copies per subject/layer; unreadable geometry/paint or exceeding
that bound fails closed as `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`. Findings use
`overlay-blend` and the last applicable overlay identity, with sampled colours.
Enumerate candidates by intersecting the closed subject bounds with the canvas
clip and inverting the completed tile transform for its four corners. With
tile centre `c=(tileInlineSize/2, tileBlockSize/2)` and rotation `R`, the
forward transform is `origin + c + R(p-c)` and the inverse is
`c + R^-1(p-origin-c)`, matching existing SVG translate/rotate serialization.
Take the resulting tile-space extents. For each axis of tile extent `T`,
indices run inclusively from `ceil(min/T)-1` through `floor(max/T)`; thus seam
touch includes both neighbours. The cap counts the Cartesian product before
ink rejection; 4096 is allowed, 4097 is not. Actual contact uses transformed ink
clipped to its tile and canvas; edge touch counts, and stroke never expands
the candidate region beyond the clipped tile.

**The as-of light cone as a translucent ground (#890).** The cone (role `as-of-cone`,
a Symbol with a gradient whose stops carry opacities) is never an ordinary opaque host.
`_ground_under` skips it, and an explicit step composites it over the host a mark, state
text or ground text truly lies on: the cone applies when it is painted after that host
and before the primitive (an opaque host painted after it hides it). The gradient is
linear and the polygon convex, so the worst ground over the stops a primitive spans is
found at the two ends of its block extent inside the gradient range: at each end where its
box meets the polygon's chord, the ground is the host colour with the cone ink composited
at the strength the gradient has there (the paint opacity times the interpolated stop
opacity). A primitive wholly inside the polygon lies on the blended grounds only; one
that straddles the edge also lies on the unblended host; one the polygon does not reach
keeps its host. The finding keeps one finding per channel, reports the worse ratio, the
cone's identifier as `groundId`, the blended colour as `groundColor` and `groundKind`
`cone-blend`; a canvas texture's or pattern's two colours are each blended. A decoration
is not judged against the cone. No floor changes, and an unreadable cone is a malformed
Scene document (`E_SCENE_CONTRAST_DOCUMENT`), never a silent skip.

**A translucent host is composited over its own ground (#1013).** A host (a label chip, a region
frame, a panel) whose `paint.opacity` is in [0, 1) is not refused: a mark or text (the `legibility` class) on it is
judged on the host's colour blended over the ground beneath it, as completed. The ground beneath is resolved by the
same rule one level down, at the same sample point, in paint order: the topmost earlier covering Rect or Symbol with a
fill, else the canvas. Each colour of the host (its fill, or the gradient sample, and its stroke ink when it is a
canvas texture or a catalogue pattern host) is `blend_over` every ground beneath it, the grounds of a texture or
pattern beneath (substrate and ink) and the grounds a cone painted between the two hosts makes (the as-of cone tints
the beneath ground, then the host is composited over it); a cone painted after the host tints the composite as it
tints an opaque host. The label is judged on every composite and the worst ratio decides, as for patterns and cones;
stacked translucent hosts recurse in paint order. The finding names the translucent host as `groundId`, the composite
as `groundColor` and `groundKind` `translucent-over-<kind of the ground beneath>` (`translucent-over-canvas`,
`translucent-over-flat`, `translucent-over-texture-ink`, `translucent-pattern-host-ink-over-canvas` for a patterned
chip, `translucent-over-translucent-over-flat` when stacked); a cone that tints the result is `cone-blend`, as above.
No floor, class or code changes. Still `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` (an error for a mark or text; the
decoration warning of #995 for a decoration), because no ground can be read: a translucent host whose opacity is not a
finite number in [0, 1], whose fill is not `#RRGGBB`, whose gradient cannot be sampled, or whose ground beneath is
one of these; and, unchanged, a decoration on a translucent host (a decoration is a tint judged against its dominant
substrate, with no ink, cone or composite ground) and note prose on a note box that is not opaque, flat and
same-source (Specification 08, C4). A translucent canvas has nothing under it and stays `E_SCENE_CONTRAST_PAINT`.

**Vector artwork behind an annotation (#848).** The parts of an annotation container's artwork are sibling `Symbol`
primitives with purpose `annotation-artwork` and the selected `annotation-artwork` or
`annotation-artwork-<slug>` role over the note box, whose bounds are the whole note.
The named role family retains the same decoration classification. Every prior same-source
layer participates in the touched-ink rule below; declaration order is preserved. A part is never a host by
bounds, so the frame ring around a note's paper is not the ground of the text in its hole, and the parts of one artwork
are never each other's ground. The artwork is judged as ink on its substrate: a label of the legibility classes (state
text, ground text, mark) whose `sourceRef` equals an earlier part's takes that part's ink as one more ground **where the
part's painted area meets the label's bounds**, and only there. A fill part is its closed outline under the non-zero
winding rule (a hole wound the other way is empty); a stroke part is its flattened path widened by half its stroke
width; a quadratic is flattened to eight chords. The ink is composited at the part's opacity over every substrate
ground already found (the note box for prose, the bar or box for a header) and the worst ratio decides, as for a
pattern; the finding names the part as `groundId`, `groundKind` `artwork-ink` and the composited `groundColor`. A label
that touches no ink is judged on the substrate alone. A decoration over the artwork keeps the dominant-substrate model
(no ink ground). Fail-closed:
a part of the label's note whose outline or opacity cannot be read is `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`, never
skipped. Note prose keeps its C4 pairing with its own opaque flat box.

**Repeated frame glyph ink.** A prior `Symbol` with the `frame-glyph` role family is never a host by its slot-sized
bounds. For a legibility-class subject, each painted frame part strictly between the resolved host and subject in
`(paintOrder, document index)` is an additional ground only where its actual fill or stroke touches the subject's
bounds; source identity does not restrict this frame ink. The existing sparse-symbol contact rules and fail-closed
paint handling apply. Resolve parts in paint order: cones before a part tint the ground beneath it, and cones after it
tint both that ground and the part's ink. A later opaque host hides earlier frame parts; a translucent host composites
over the frame ink beneath it. Keep the underlying ground as a conservative alternative where the frame does not cover
the whole subject. Decorations retain their dominant-substrate rule, and annotation artwork keeps its separate
same-source rule above.

A dual-channel Rect or Symbol is evaluated at a separate painted sample for
each channel: fill at bounds centre, stroke at the left-edge block midpoint.
Either channel may carry a data mark's 3.0:1 visibility floor, and the
finding records the winning channel and its own ground. Theme-supplied mark
outlines may therefore preserve a category-coloured fill when the same
category also colours its background. No outline is inferred by Scene or an
adapter (#459).

**Multipart mark figures (#1178).** MARK-classified `Symbol` parts of one
completed placement are one contrast figure, not substrates for each other.
The existing terminal identity forms `:partN` and `:part:N` identify that
placement within one surface; source, purpose, role, bounds and slot metadata
must agree. A source or role alone never groups distinct placements. All sibling
parts are excluded throughout external-ground resolution, including translucent
host recursion. Each part keeps the completed painted-sample, pattern and cone
rules above. As with a dual-channel mark, any readable part/channel may carry
the figure's visibility floor; one observation records the best ratio and its
actual part identity, channel and ground, with document-order ties. Malformed
paint and unsupported external grounds remain one reasoned failure rather than
being hidden by a visible sibling. A part with several effective pattern-pair
obligations contributes its worst pair; figure selection must not allow a good
pair to mask another required pair of that part. Singleton marks are unchanged. This does not
group annotation artwork layers or change their touched-ink contract.
