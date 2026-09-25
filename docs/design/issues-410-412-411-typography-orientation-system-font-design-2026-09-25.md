# Design — Measured Typography, Rotated Runs, and Draft System Fonts

**Status:** proposed for architecture review.
**Issues:** #410, #412, #411.

## Decision

Chrona will represent every text run with a completed, renderer-neutral
`TextTreatment` and `TextOrientation`.  Layout measures the canonical painted
string using that treatment, emits occupied geometry after orientation, and
Scene carries the same completed values to every adapter.  No adapter may
transform, track, select numeric figures, rotate, or substitute text on its
own.

Host fonts are not a third immutable font locator.  They are an explicit
draft-only resolution result, constructed before rendering and rejected by all
immutable/evidence entry points.

## Text treatment (#410)

`ThemeTokenView.typography()` is replaced by a typed `TextTreatment`:

| Field | Owner | Finite/value contract |
| --- | --- | --- |
| `family`, `weight`, `font_size`, `line_height` | Theme | existing declared values |
| `transform` | Theme | `none`, `uppercase`, `lowercase`, `capitalize` |
| `letter_spacing_em` | Theme | finite decimal range in em; resolved to `font_size * em` before measurement |
| `numeric_spacing` | Theme | `proportional` or `tabular` |

The source string remains provenance.  Layout first applies the deterministic
Unicode transform, then measures and stores the resulting painted string.
`TextPlacement` and `TextLayout` retain source and painted content where they
differ, so ellipsis, wrapping, bounds, inspection Scene text, accessibility,
and adapter output agree exactly.

Tabular figures are not an adapter feature toggle.  Declared metrics v3 adds
the explicitly measured tabular digit advances for a font asset; a role that
selects `tabular` is rejected when its selected face lacks those advances.
The raster/font payload is the same selected face and OpenType feature request.
SVG, PDF, Typst, and TikZ emit the already selected `font-variant-numeric`
setting; their paint is not permitted to choose a different feature.  This
keeps a signed-days table column's numeric alignment consistent with Layout.

## Orientation and layout direction (#412)

`writingMode` is replaced, without a compatibility reader, by two concepts in
Layout Profile v0.8:

* `flowDirection` is a finite layout-axis choice.  The review surface currently
  supports only `horizontal`; dependency-network may explicitly opt into its
  own finite vertical flow when its node geometry supports it.
* `TextOrientation` is a completed geometry value on a text placement:
  `horizontal`, `rotate-cw`, or `rotate-ccw`.  It is a View-declared label or
  header intent, not a Theme property and not a claim of vertical-script/CJK
  composition.

For a horizontal run with measured width `W` and line-block height `H`, a
rotated completed placement occupies `(H, W)`.  Layout performs fit, collision,
overflow, clipping, and slot ownership against that occupied rectangle.  The
completed text layout records a baseline anchor and rotation angle; adapters
apply only that supplied transform around the anchor.  Multiline text is one
measured block rotated as a whole.  A rotated run therefore does not silently
reuse horizontal collision bounds.

The first public use is a deliberately narrow rotated axis/header label corpus
fixture.  CJK vertical shaping, glyph orientation, and automatic rotation are
out of scope.

## Draft system fonts (#411)

`chrona render` and draft workspace rendering gain an explicit
`--system-fonts` opt-in.  Theme family/weight remains the request; the opt-in
causes a `SystemFontResolver` to locate one exact local font file before
Layout.  Resolution is an injected platform service with production backends
and a fake-test backend.  It returns either one unambiguous file or a
family/weight-specific diagnostic.  It never substitutes a neighbouring family
or a renderer default.

The resolver generates metrics from that file and returns a `DraftFontResolution`
containing the requested family/weight, byte identity, metrics identity, and
nonportable provenance flag.  It is held by `DraftRender`/`RenderRequest`, not
by `RenderContextContract`, Store data, snapshot closure, or generated Scene.
PNG receives that exact path after Layout has used its metrics.  SVG receives
the declared family and completed geometry; draft provenance identifies the
result as nonportable without serializing host paths.

`materialize` and immutable `render-review` accept only declared context/package
font pairs and reject any nonportable font-resolution object before reading
evidence inputs.  Existing `skip_system_fonts=True` remains true for immutable
raster output.  Draft PNG enables only the resolved exact file, never global
host discovery.

## Authority and data flow

```text
Theme role + View label orientation       Draft CLI opt-in + Theme family
              |                                      |
       TextTreatment / TextOrientation       DraftFontResolution
              |                                      |
              +------------ Layout measurement -------+
                                   |
                         completed TextPlacement
                                   |
                          Scene TextLayout primitive
                                   |
                    SVG / PNG / PDF / Typst / TikZ projection
```

Theme selects only finite treatment.  View selects semantic text and where an
orientation is allowed.  Layout alone computes transformed content, measured
geometry, and rotation.  Scene carries completed values.  The adapter only
serializes them.  Draft resolution supplies a file to measurement and raster
paint but has no authority over semantic selection or geometry.

## Migration and exclusions

All shipped themes migrate atomically to Theme v0.11 with explicit defaults:
`none`, `0em`, and `proportional`.  All layouts migrate atomically to
Layout Profile v0.8; no v0.7 reader remains.  Existing visible output must be
byte-stable except for designated typography/orientation evidence slides.

No system locator is added to render-context schemas.  No system font is
materialized, copied, pinned into a Context, or used by CI corpus evidence.
No adapter-specific transform, browser font lookup, arbitrary OpenType feature
string, automatic rotation, or full vertical/CJK writing system is introduced.

## Acceptance criteria

1. Changed text has identical measured and painted content/spacing/numeric
   feature/orientation across all supported targets.
2. Rotated occupied bounds control fit and collision, with corpus Scene/SVG/PNG
   evidence.
3. Signed numeric table facts use measured tabular advances and align publicly.
4. Draft system-font resolution uses the exact measured file and returns a
   diagnostic for absent/ambiguous requests; immutable rendering and
   materialization reject nonportable resolution.
5. Schema closure, public corpus reproducibility, full tests, conformance,
   wheel smoke, generated artifact review, and three-platform CI pass.
