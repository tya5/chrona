# Portable Visual Capabilities

**Status:** Correcting v0.6 target-fidelity contract (#349)
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
- `stroke.line-cap` / `stroke.line-join` (closed values `butt|round|square` and
  `miter|round|bevel`).

No raw SVG/XML/CSS, transform, arbitrary definition, filter graph, rectangular
or path clip, mask, blend, image, radial gradient, glow/blur, animation,
script, HTML, or network asset is admitted. A future target cannot make a
deferred capability available by silently interpreting package data.

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
| `chrona-output/visual/v0.6-svg` | SVG | all initial v0.6 IDs |
| `chrona-output/visual/v0.6-png` | PNG through pinned resvg | all initial v0.6 IDs |

PDF, Typst, and TikZ have no v0.6 profile. PDF's current svglib/ReportLab route
does not preserve the required drop-shadow; it must reject a rich profile before
serialization rather than silently dropping treatment. A future PDF profile
requires independent per-capability evidence and a new profile identifier.

Each requested gradient, shadow, and stroke finish independently declares either
`required` or `decorative-optional`; it is not one role-wide value. A baseline
profile permits deterministic omission only for an unsupported
`decorative-optional` treatment.
Required unsupported capability fails before serialization with
`E_VISUAL_CAPABILITY_UNSUPPORTED`. Optional omission is performed by the Scene
resolver only when the target profile declares omission allowed; the adapter
never decides. Invalid profile/value/fidelity/limit uses diagnose as
`E_VISUAL_CAPABILITY_PROFILE`, `E_VISUAL_CAPABILITY_VALUE`,
`E_VISUAL_CAPABILITY_FIDELITY`, or `E_VISUAL_CAPABILITY_LIMIT`, with the exact
role property pointer. `VALUE` identifies incomplete or malformed treatment
binding; `FIDELITY` identifies an invalid treatment fidelity; `LIMIT` identifies
a finite out-of-range angle, blur, opacity, or declared stop count.

## 4. Accessibility, security, and determinism

A treatment is decorative unless its non-colour distinction is separately
represented by existing semantic role, text, marker, pattern, or source
metadata. Shadow/gradient/clip cannot carry a required meaning alone. They
cannot load bytes, execute code, create DOM behavior, or alter Commands.
Finite profile limits and exact resolved parameters make output reproducible.

## 5. Packages and Design Space

A future Presentation Package may declare a finite required/optional subset of
this vocabulary only after package acquisition is re-designed. A registry may
compare that declaration with a target profile without rendering; it cannot
select a target or alter a closure. Design Space may expose a named appearance
only when it resolves to these owner fields and profile requirements.
