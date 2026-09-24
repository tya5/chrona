# Issues #353, #351, #352, and #358 — Output Portability Design

**Decision:** Accepted.

## #353 — Visual-capability diagnostics

`E_VISUAL_CAPABILITY_VALUE`, `E_VISUAL_CAPABILITY_FIDELITY`, and
`E_VISUAL_CAPABILITY_LIMIT` stay Scene-policy diagnostics.  Their exception
object gains an optional public detail, so the existing use-case boundary can
emit field-specific values and bounds without moving Theme validation into a
renderer.  Parametrized Scene tests cover malformed, invalid-fidelity, and
each bounded-value path.  Pillow is declared in the render extra because the
public PNG pixel assertion directly imports it.

## #351/#352 — Immutable font closure

The current record binds only a metrics JSON; it cannot prove that Layout and
an output adapter use the same font.  Render Context advances to v0.13 and
replaces each loose metric asset with this required shape:

```yaml
fontMetrics:
  algorithm: declared-metrics-v2
  assets:
    - family: Noto Sans CJK JP
      weight: 400
      metrics: {path: font_metrics/noto-sans-cjk-jp-regular-v1.json, contentIdentity: sha256:...}
      font: {path: fonts/noto-sans-cjk-jp-v1.ttf, contentIdentity: sha256:...}
```

The metrics table's `sourceContentIdentity` must equal the declared font
identity.  One Noto Sans CJK JP variable TTF, sourced from the official Noto
CJK project and distributed with its SIL Open Font License notice, is bundled
as the default 400/700 font asset.  It covers the existing Latin corpus and
Japanese text; the metrics generator instantiates the declared `wght` axis
for each measured weight while retaining the identity of the source variable
font.  Public Themes and all Contexts migrate atomically to this one family.
There is no Nimbus-only compatibility descriptor or host-font fallback.

`FontMetrics.width` rejects the first missing non-control glyph with
`E_FONT_GLYPH_UNAVAILABLE`, including family, code point, and source text.
Missing declared files/identities remain `E_FONT_METRICS_UNAVAILABLE` at the
Context closure boundary.  This makes unsupported script coverage explicit
instead of treating `.notdef` width as geometry.

Wrapping remains deterministic and dependency-free.  It retains word wrapping
for whitespace-delimited text and adds a bounded CJK rule: an ideograph,
Hiragana, Katakana, or Hangul boundary is a break opportunity; closing
punctuation and prolonged-sound marks attach to their predecessor, and opening
punctuation attaches to its successor.  This is an explicit small policy, not
a partial Unicode line-break engine.

Renderer factories receive the resolved asset root and Context font records.
PNG passes only declared `font_files` to resvg and sets
`skip_system_fonts=True`; its artifact identity includes ordered font content
identities.  PDF registers the same declared TrueType font before converting
the completed SVG; if a declared font cannot be registered, PDF fails before
artifact emission rather than claiming `accessibleText`.  SVG remains a
completed-scene serializer and does not load font bytes.  Draft render,
materialization, example materialization, and snapshot closures all copy or
resolve both metrics and font bytes under the same Context identity.

The release includes Japanese SVG/PNG/PDF evidence, a missing-glyph negative
case, a cross-host PNG byte pin, and documentation for generating and using a
bring-your-own metrics/font pair.

## #358 — Portable Layout requirements

Layout Profile v0.4 owns the finite token names it needs.  A root-level
`requiredThemeTokens` is a sorted, duplicate-free list of number-token IDs.
The profile resolver gathers every `{token: ...}` distance use and requires it
to equal that declaration exactly.  It then checks that the selected Theme
provides each declared name as a finite non-negative number.  Missing,
extraneous, and non-number requirements receive distinct stable diagnostics;
`E_LAYOUT_TABLE_OVERFLOW` remains an allocation result and is not weakened.

This is preferable to Layout defaults: a Layout's spacing and panel geometry
remain authored by its Layout resource, while a Theme supplies values for a
declared interface.  The interface makes portability observable without
turning Theme into a hidden Layout selector.  All public Layouts migrate in
one schema/version slice, then a same-View Context pair proves the portable
composition comparison under a fixed Theme/Scheme.  If that pair fails table
feasibility, it is deferred separately rather than changing appearance.

## Whole-architecture review

Font asset resolution is Context closure work; Layout measures only resolved
metrics, Scene carries their identity, and adapters consume the declared font
files without policy inference.  The font schema has no renderer-specific
fallback setting.  The Layout interface is validated before allocation and
does not introduce a Theme-to-Scene or renderer-to-Theme edge.  All new
diagnostics cross the existing use-case boundary; renderers remain completed
Scene serializers.  These choices preserve deterministic offline materialize
and prevent a gallery fixture from becoming an exception mechanism.
