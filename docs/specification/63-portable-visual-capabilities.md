# Portable Visual Capabilities

**Status:** Delivered (corrected v0.6 target-fidelity contract)
**Owns:** renderer-neutral visual capability profiles, completed Scene visual
effects, fidelity, limits, and target admission. It does not own geometry,
semantic selection, Layout, concrete color literals, package acquisition, or
raw target syntax.

## 1. Contract

Visual capabilities compose over completed Scene geometry:

```text
Theme + Color Scheme -> completed visual treatment -> Scene primitive -> target profile -> adapter
```

The initial v0.6 vocabulary is closed:

- `paint.linear-gradient` (exactly two ordered stops);
- `effect.drop-shadow` (one layer, finite offsets, blur `0..64`, opacity `0..1`);
- `effect.glow` (#587: one centred halo, blur `(0, 64]` as a standard deviation in px, opacity `0..1`);
- `stroke.wobble` (#588: one deterministic perturbation of a stroke's geometry, section 8);
- `stroke.line-cap` / `stroke.line-join` (closed values `butt|round|square` and
  `miter|round|bevel`).

No raw SVG/XML/CSS, transform, arbitrary definition, filter graph, rectangular
or path clip, mask, blend, generic image, arbitrary radial gradient, general blur, animation,
script, HTML, or network asset is admitted. A future target cannot make a
deferred capability available by silently interpreting package data.
Section 1.1 admits only the finite clipped surface radial treatment (#888),
not raw target gradient syntax or an arbitrary effect graph.

### 1.1. Transparent surface treatments (#888)

Ink-only periodic canvas paints use existing `paint.pattern-geometry` and
ordinary opacity. Required SVG/PNG layers are admitted in profiles that support
patterns; unsupported targets fail before serialization. Named
`textureFidelity` (`required` by default, or `decorative-optional`) admits only
whole-layer omission, never an opaque tile, flattened substitute or recolouring.
An omitted ink-only texture/overlay reports `I_VISUAL_TREATMENT_OMITTED` with
treatment `canvas-texture`/`canvas-overlay`; failures point to the selected
role's `textureFidelity`. Existing opaque textures retain their contract.

The distinct `paint.radial-gradient` capability admits a finite two-opacity
surface fade, used only by `canvas-overlay-gradient`. Layout completes its
positive elliptical radii, centre, canvas region and inner-stop offset;
Scene completes fixed ink colour, stop alpha and fidelity. Radius is
`sqrt(((x-cx)/rx)**2 + ((y-cy)/ry)**2)`. Alpha is 0 through the inner stop,
linear to role opacity at radius 1, and constant beyond 1. Only alpha varies;
colour stays fixed, and composition uses the existing sRGB-encoded-channel
alpha compositor (Spec46). Bounds are the completed canvas clip and fixed
layer/stop structure, not an arbitrary radius threshold. Stops share one Scheme-resolved ink; no raster, filter,
arbitrary stop program or adapter-completed geometry is admitted.
Optional Scene v0.7 `paint.radialGradient` preserves every existing valid
document and absent-field serialization, like glow/wobble/stop-alpha additions.
It cannot coexist with linear `gradient`, pattern or another effect.

Rich v0.6 SVG/PNG profiles and their v0.7 icon-profile extensions admit radial
paint; baseline and non-SVG/PNG routes do not.
Named `gradientFidelity` defaults to `required`: unsupported is
`E_VISUAL_CAPABILITY_UNSUPPORTED` at
`/body/roles/canvas-overlay-gradient/gradientFidelity`; `decorative-optional`
omits the whole layer and reports treatment `canvas-overlay-gradient`.
Omission preserves content geometry/paint and the other independent layers.
SVG serializes closed radial data and non-interactive overlays; PNG uses pinned
resvg. Typst/TikZ/PDF never receive unsupported completed treatments.

## 2. Ownership and completed Scene data

Theme declares semantic role bindings. Color Scheme resolves every gradient
stop and shadow color through existing Scheme intents; literals are forbidden.
Theme may bind finite number tokens for gradient angle and shadow offset/blur,
and finite enum tokens for stroke cap/join. Scene resolves these into immutable
`LinearGradient`, `DropShadow`, and `StrokeFinish` values. Layout continues to
supply every bound and must not select treatment. An adapter receives only
completed values and cannot read Theme/Scheme or choose a fallback.

An author declares one angle in degrees clockwise from the positive Layout
inline axis. Scene converts that angle and the completed primitive (or canvas)
bounds into finite start/end points in the Layout coordinate plane. The line
through the bounds centre reaches the furthest projected bound corner in each
direction, so its visible direction is invariant to aspect ratio. `LinearGradient`
therefore carries those completed endpoints and two normalized stops, not an
adapter-interpreted angle. `DropShadow` has resolved color, offset, blur,
opacity, and one declared fidelity; `StrokeFinish` has cap/join. Every number
is finite. A primitive may
have at most one gradient and one shadow. Effects never alter source identity,
semantic purpose, accessible alternative, or Layout geometry.

## 3. Profile and fidelity

A Render Context names one exact target profile. A profile declares supported
IDs and limits; it is an immutable evaluation input. The valid identifiers are:

| Profile | Target | Supported capability IDs |
| --- | --- | --- |
| `chrona-output/visual/v0.5-baseline` | SVG, PNG, PDF, Typst, TikZ | none |
| `chrona-output/visual/v0.6-svg` | SVG | all initial v0.6 IDs, `effect.glow`, `stroke.wobble` and `paint.radial-gradient` |
| `chrona-output/visual/v0.6-png` | PNG through pinned resvg | all initial v0.6 IDs, `effect.glow`, `stroke.wobble` and `paint.radial-gradient` |

PDF, Typst, and TikZ have no v0.6 profile. PDF's current svglib/ReportLab route
does not preserve the required drop-shadow; it must reject a rich profile before
serialization rather than silently dropping treatment. A future PDF profile
requires independent per-capability evidence and a new profile identifier.

Each requested gradient, shadow, glow, wobble, and stroke finish independently declares either
`required` or `decorative-optional`; it is not one role-wide value. A baseline
profile permits deterministic omission only for an unsupported
`decorative-optional` treatment.

Shipped Draft preset-library entries must render a fresh starter project under
the default Draft target/profile. An unsupported decorative effect may be
`decorative-optional` only when the flat fallback is a complete visible
treatment. A preset may not silently select or upgrade the target profile;
rich-profile output remains explicitly selectable.
Required unsupported capability fails before serialization with
`E_VISUAL_CAPABILITY_UNSUPPORTED`, its exact Theme role property or View icon
binding pointer, and a capability-specific message. Optional omission is performed by the Scene
resolver only when the target profile declares omission allowed; the adapter
never decides. Invalid profile/value/fidelity/limit uses diagnose as
`E_VISUAL_CAPABILITY_PROFILE`, `E_VISUAL_CAPABILITY_VALUE`,
`E_VISUAL_CAPABILITY_FIDELITY`, or `E_VISUAL_CAPABILITY_LIMIT`, with the exact
role property pointer. `VALUE` identifies incomplete or malformed treatment
binding; `FIDELITY` identifies an invalid treatment fidelity; `LIMIT` identifies
a finite out-of-range angle, blur, opacity, or declared stop count.

When Scene omits a `decorative-optional` treatment, it MUST retain a typed
disposition naming the authoring role, treatment, selected profile, target,
Theme property pointer, and the first same-target profile that could paint it
(if one exists). Repeated primitives with the same role/treatment/profile/target
produce one info diagnostic, not one per primitive. Inspection Scene diagnostics
carry `I_VISUAL_TREATMENT_OMITTED:role=<role>;treatment=<treatment>;profile=<selected>;paintable=<same-target-profile-or-none>`;
the CLI emits the same fact at `info` severity. This is not a layout failure.
The profile registry, not the adapter or preset, chooses the suggestion. No
profile is selected or upgraded on the author's behalf. The Theme role/property
admission rule in Specification 07 is evaluated first; it distinguishes a
supported treatment omitted by this profile from a property no consumer can
carry under any profile.

## 4. Accessibility, security, and determinism

A treatment is decorative unless its non-colour distinction is separately
represented by existing semantic role, text, marker, pattern, or source
metadata. Shadow/gradient/clip cannot carry a required meaning alone. They
cannot load bytes, execute code, create DOM behavior, or alter Commands.
Finite profile limits and exact resolved parameters make output reproducible.

## 5. Packages and Design Space

Specification 64 is the sole narrow exception for an immutable, catalog-owned,
normalized SVG/PNG **icon** asset. It owns its own source validation, closure,
Scene primitive, and exact target profiles. This specification continues to defer a
general Image capability, arbitrary raw SVG, and target asset interpretation.

A future Presentation Package may declare a finite required/optional subset of
this vocabulary only after package acquisition is re-designed. A registry may
compare that declaration with a target profile without rendering; it cannot
select a target or alter a closure. Design Space may expose a named appearance
only when it resolves to these owner fields and profile requirements.

## 6. Closed capability ceiling

The renderer-neutral vocabulary is governed by the typed closed capability
ceiling, rather than by target-adapter affordances. Its generated dispositions
and source-observation evidence are published in the
[presentation capability prior-art matrix](../research/presentation/presentation-capability-prior-art.md).
The matrix is review evidence only: it cannot configure a profile, adapter, or
presentation resource.

## 7. Glow (#587)

A Theme role that admits a shadow admits a glow: the properties `glowColor` (a
Color Scheme binding `<role>.glowColor`), `glowBlur` (`0 < blur <= 64`),
`glowOpacity` (`0..1`) and `glowFidelity` (`required` or `decorative-optional`).
Colour, blur and opacity are declared together or not at all
(`E_VISUAL_CAPABILITY_VALUE` at `glowBlur`); out-of-range values are
`E_VISUAL_CAPABILITY_LIMIT`; a role declares a shadow or a glow, not both
(`E_VISUAL_CAPABILITY_VALUE`). The canvas, Icon-shared and shared `text` roles do
not admit it. Scene completes `Glow(color, blur, opacity, fidelity, region)`:
`region` is the primitive's visible extent (for a Path, the box of its points)
grown by three blur on every side and intersected with the canvas, so the halo
never leaves the slide and is no part of the primitive's bounds, collision or
hosting. `effect.glow` is in the rich profiles (`v0.6-svg`, `v0.6-png`, `v0.7-svg`,
`v0.7-png`) and not in the baseline: a `decorative-optional` glow is omitted there
with `I_VISUAL_TREATMENT_OMITTED:...;treatment=glow;...;paintable=<first rich
profile of the target>`, a `required` glow is `E_VISUAL_CAPABILITY_UNSUPPORTED`
at `/body/roles/<role>/glowBlur`. SVG draws it as one filter per glowing element
over `region` (`filterUnits="userSpaceOnUse"`): the Gaussian-blurred alpha,
flooded with the colour at the opacity, merged twice under the source graphic;
PNG is that SVG through resvg. The drop-shadow filter is unchanged. A Scene that
carries a glow is written as `chrona/scene/v0.7` (optional `paint.glow`).

## 8. Hand wobble (#588)

A Theme role whose completed primitive is a Rect or a Path admits four properties:
`wobbleAmplitude` (px, `0 < amplitude <= 16`), `wobbleWavelength` (px,
`4 <= wavelength <= 1000`), `wobbleSeed` (an integer, `0 <= seed < 2^32`) and
`wobbleFidelity` (`required` or `decorative-optional`). The first three are declared
together or not at all (`E_VISUAL_CAPABILITY_VALUE` at `wobbleAmplitude`); out-of-range
values are `E_VISUAL_CAPABILITY_LIMIT` at the property; the canvas, text, Icon-shared and
`canvas-texture` roles do not admit them. It applies to **a Rect that has a stroke** (the
fill and the stroke both follow one closed perturbed outline) and **a Path** (each
sub-path); a Symbol, Text or Icon, a fill-only Rect, a Rect with a pattern or an image
fill, and a clip host keep their exact geometry, because a pattern region, an image tile
and a clip are defined to equal the rectangle.

Scene completes `StrokeWobble(amplitude, wavelength, seed, fidelity, closed, outline)`
from the primitive's Layout geometry; adapters draw `outline` verbatim and never
perturb. The primitive's `bounds`, `points` and path commands stay the Layout values, so
placement, collision, hosting, label fitting, contrast grounds and perceptibility are
the same with and without the treatment. The ink of a wobbled primitive lies within the
effective amplitude of the nominal outline, so its extent is the bounds grown by at most
that amplitude plus half the stroke width; a glow region is computed from the nominal
extent.

**The algorithm is normative and platform independent.**

1. *Nominal outline.* A Rect is its clockwise outline from the top-left (a corner
   radius is flattened to the quadratic Bezier whose control point is the sharp corner,
   evaluated at `t = 0.25, 0.5, 0.75`, `1`); a Path is each sub-path, each quadratic
   flattened the same way in four steps; consecutive equal points are dropped.
2. *Cells.* With `P` the outline's length, `n = floor(P / wavelength + 0.5)` (at least 2
   for a closed outline, 1 for an open one) and the realised wavelength `P / n`. Each
   edge is split into `max(1, ceil(length / (P / n / 4)))` equal parts, every nominal
   vertex kept. More than 8192 points is `E_VISUAL_CAPABILITY_LIMIT` at
   `wobbleWavelength`.
3. *Generator.* `mix(x)` is the splitmix64 finalizer of `x` modulo `2^64`. The stream of
   one outline is `mix(mix(seed) XOR fnv1a64(utf8(scene id)) XOR (sub-path index << 56))`,
   where `fnv1a64` is the 64-bit FNV-1a hash. Lattice point `k` has the value
   `(mix(stream XOR (k * 0xD1B54A32D192ED03 mod 2^64)) >> 11) / 2^53 * 2 - 1`, an exact
   double in `[-1, 1)`. The seed therefore selects a family of lines and each primitive
   draws its own member of it, stably.
4. *Noise.* At arc length `s` the position is `u = s * n / P`, `k = floor(u)`,
   `t = u - k`, `w = t * t * (3 - 2t)`, and the noise is `L(k) + (L(k + 1) - L(k)) * w`
   (the index wraps modulo `n` for a closed outline, so it closes without a seam).
5. *Displacement.* Each vertex moves along its unit normal (the normalised sum of the
   adjacent unit segment normals, the segment normal at an open end, `(dy, -dx)` of a
   clockwise outline, so outward) by `amplitude * noise * envelope`. The envelope is 1 for
   a closed outline and `min(1, s / realised, (P - s) / realised)` for an open one, so both
   end points and a marker keep their place. A Rect's amplitude is limited to a quarter of
   its shorter side.
6. *Arithmetic.* Only `+ - * /`, `sqrt`, `floor`, `ceil` and integer arithmetic; no
   `sin`, `cos`, `pow`, `exp`, `hypot`, `random`, hash or iteration-order dependence.
   Coordinates are rounded with `round(value, 3)`, and SVG writes them with three decimals.

`stroke.wobble` is in the rich profiles (`v0.6-svg`, `v0.6-png`, `v0.7-svg`, `v0.7-png`)
and not in the baseline: a `decorative-optional` wobble is omitted there with
`I_VISUAL_TREATMENT_OMITTED:...;treatment=wobble;...;paintable=<first rich profile of the
target>` and the primitive is drawn straight; a `required` wobble is
`E_VISUAL_CAPABILITY_UNSUPPORTED` at `/body/roles/<role>/wobbleAmplitude`. The Typst and
TikZ adapters refuse a Scene that carries a `required` wobble (as they refuse a pattern)
and draw an optional one straight. SVG draws a wobbled Rect as one closed `<path>` carrying
the Rect's fill, stroke and filter attributes, and a wobbled Path as one `<path>` of
`M...L...` sub-paths with its markers; PNG is that SVG through resvg, so the two share
every coordinate. A Scene that carries a wobble is written as `chrona/scene/v0.7`
(optional `paint.wobble`).

## 9. As-of light cone (#890)

The cone (Specification 07, role `as-of-cone`) is gradient paint and needs
`paint.linear-gradient`; no capability ID is added. `LinearGradient` gains optional
`stop_opacities` (one opacity per stop, `0..1`): a completed fact, so the same
fidelity, profile and omission rules govern it. Scene completes the cone's gradient from
its polygon: start at the apex row, end at the foot row, two stops of the role ink at
opacities 1 and 0, so the ground it fades into is never named. Under a profile that
does not admit the gradient (the baseline), a `decorative-optional` cone is **omitted
whole** (never a flat ink polygon) and reported as
`I_VISUAL_TREATMENT_OMITTED:role=as-of-cone;treatment=as-of-cone;profile=<selected>;paintable=<first rich profile of the target>`;
a `required` cone (the default when `gradientFidelity` is absent) is
`E_VISUAL_CAPABILITY_UNSUPPORTED` at `/body/roles/as-of-cone/coneSpread`. The treatment
name `as-of-cone` joins the closed set of omitted treatments. A shipped Draft preset
may declare a cone `decorative-optional`: no cone is a complete visible treatment. PDF,
Typst and TikZ never receive a gradient. A Scene whose gradient carries stop opacities
is written as `chrona/scene/v0.7` (optional `opacity` on a gradient stop).

## 10. Annotation artwork (#848)

The artwork of a rectangle annotation container (Specification 07) is a few `Symbol` parts. A fill part needs `mark.symbol-outline`, which every profile admits; a stroke part carries a required line cap and join and so needs `stroke.line-cap` and `stroke.line-join`. Where the selected profile lacks them and a completed artwork layer has a stroke part, that layer's selected Theme role's `artworkFidelity` decides: `required` (the default) is `E_VISUAL_CAPABILITY_UNSUPPORTED` at `/body/roles/<selected-role>/artworkFidelity`; `decorative-optional` omits the **whole** affected layer independently, including when several layers reuse one role and reports `I_VISUAL_TREATMENT_OMITTED:role=<selected-role>;treatment=annotation-artwork;profile=<selected>;paintable=<first rich profile of the target>`. The treatment name `annotation-artwork` joins the closed set of omitted treatments. Scene decides at the typed layer boundary before flattening parts, without a new public Scene field. The legacy object retains its exact role, pointer and omission identity. Layout geometry does not depend on the profile. Typst and TikZ never receive a stroked artwork part; Typst receives no `Symbol` at all.

### 10.1 Catalogue-glyph frame borders (#888)

The independent `frame-glyph` or `frame-glyph-<slug>` role uses the same
fill/stroke capabilities and `artworkFidelity` rule. Layout completes one
typed glyph batch per framed node; Scene admits or omits that **whole border**
before flattening its parts, never individual bulbs or corners. An unsupported
required stroke fails at `/body/roles/<selected-role>/artworkFidelity`; optional
omission uses treatment `frame-glyph` and leaves the independent region-frame
panel and content unchanged. Neither profile admission nor omission changes
Layout geometry. The existing target restrictions on `Symbol` still apply.
