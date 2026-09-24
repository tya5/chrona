# Declared Font Assets

Chrona measures text from the exact metrics declared by a Render Context.
PNG/PDF additionally use identity-pinned font bytes; SVG does not load them.
It never uses a host-installed font at render time. The bundled default is the
small OFL `Noto Sans` Regular/Bold pair. Install `chrona[fonts-cjk]` to use the
separately distributed OFL `Noto Sans JP` pair for Japanese text.

## Context closure

`chrona/render-context/v0.14` requires a metrics record for every family/weight
that its Theme can select. A font record is required only for PNG/PDF. Each
record is either Context-relative or an identity-named installed package asset.

```yaml
fontMetrics:
  algorithm: declared-metrics-v2
  missingFont: diagnose
  assets:
    - family: Acme Sans
      weight: 400
      metrics:
        locator: {provider: context, address: fonts/acme-regular.metrics.json}
        contentIdentity: sha256:<metrics-bytes>
      font:
        locator: {provider: context, address: fonts/acme-regular.ttf}
        contentIdentity: sha256:<font-bytes>
```

Package records use `{provider: package, identity: chrona-fonts-noto-cjk,
address: ...}`. The materializer copies and verifies metrics for every target,
and copies font bytes only for PNG/PDF, rewriting copied records to Context
locators. A missing glyph is rejected as `E_FONT_GLYPH_UNAVAILABLE`; it is
never measured as `.notdef`.

## Target and draft policy

SVG needs only pinned metrics, so a metrics-only descriptor can produce a
deterministic SVG layout without redistributing a licensed font. PNG and PDF
need every declared font byte; an absent byte path is rejected as
`E_FONT_METRICS_UNAVAILABLE` and names that path.

Draft-only descriptors may set `missingFont: substitute`. Chrona then measures
the explicitly packaged fallback for a missing supported glyph and emits a
`W_FONT_GLYPH_SUBSTITUTED` JSON warning to stderr. Immutable Render Contexts
and the public materializer reject `substitute`; it is never corpus evidence.

Use OFL or another redistribution-permitting license for anything committed to
a corpus or distributed in a package. A licensed font may be used for a
private user's PNG/PDF, or its metrics may be shared for SVG layout, but a
materialized raster snapshot copies its bytes and must not be redistributed
unless its license permits that use.

## Bring your own pair

Generate the metrics from the exact font bytes that will ship with the Context.
For variable fonts, instantiate the selected weight before measurement:

```sh
python tools/generate_font_metrics.py fonts/acme-vf.ttf fonts/acme-regular.metrics.json \
  --family "Acme Sans" --weight 400 --axis wght=400
```

For a non-evidence draft render, put the descriptor above in `fonts.yaml` and
pass it explicitly. Asset paths resolve relative to that descriptor:

```sh
chrona render project.yaml --view view.yaml --theme theme.yaml --scheme scheme.yaml \
  --layout layout.yaml --font-metrics fonts.yaml --output review.svg
```

Declare every weight selected by the Theme. A font identity is part of PNG/PDF
adapter identity, `resvg` receives only declared `font_files` with system fonts
disabled, and ReportLab receives the same declared TTF files.
