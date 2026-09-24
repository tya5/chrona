# Declared Font Assets

Chrona measures text and rasterizes PNG/PDF from the exact font pair declared
by a Render Context. It never uses a host-installed font as a fallback. The
bundled default is `Noto Sans CJK JP`, distributed with its OFL license under
`src/chrona/resources/fonts/`; it supports Japanese text for SVG, PNG, and PDF.

## Context closure

`chrona/render-context/v0.13` requires a metrics and font record for every
family/weight that its Theme can select. Both paths are relative to the Context
asset root and both content identities are required.

```yaml
fontMetrics:
  algorithm: declared-metrics-v2
  missingFont: diagnose
  assets:
    - family: Acme Sans
      weight: 400
      metrics:
        path: fonts/acme-regular.metrics.json
        contentIdentity: sha256:<metrics-bytes>
      font:
        path: fonts/acme-regular.ttf
        contentIdentity: sha256:<font-bytes>
```

Example materializers first resolve these paths below the example directory,
then use a packaged resource only when no local asset exists. The materialized
snapshot copies and verifies both payloads. A missing glyph is rejected as
`E_FONT_GLYPH_UNAVAILABLE`; it is never measured as `.notdef`.

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
