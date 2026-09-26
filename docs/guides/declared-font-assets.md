# Declared Font Assets

Chrona measures text from the exact metrics declared by an immutable Render
Context. PNG/PDF additionally use identity-pinned font bytes; SVG does not
load them. Immutable rendering never uses a host-installed font. The bundled default is the
small OFL `Noto Sans` Regular/Bold pair. The separately distributed OFL
`Noto Sans JP` provider is installed explicitly for repository development:
`pip install -e packages/chrona-fonts-noto-cjk`. It is not advertised as a
primary-package extra until that provider is published to an installable index.

## Context closure

`chrona/render-context/v0.16` requires a metrics record for every family/weight
that its Theme can select. A font record is required only for PNG/PDF. Each
record is either Context-relative or an identity-named installed package asset.

```yaml
fontMetrics:
  algorithm: declared-metrics-v3
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

Every primary face also records proportional (`pnum`) and tabular (`tnum`)
advances for ASCII digits. Layout chooses the already-resolved `numericSpacing`
feature from the Theme before it measures a numeric text run; adapters project
that same feature rather than choosing figures independently. A draft-only
character substitute may omit those maps because it never supplies a primary
face's numeric policy.

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

### Installed font for a private draft PNG

For a one-off SVG or PNG that is not evidence, `chrona render --system-fonts`
can use the exact installed faces named by the Theme. It is an explicit,
machine-local opt-in: Chrona uses exact packaged or `--font-metrics`-declared
faces first, then resolves only missing Theme family/weight pairs through
fontconfig. The selected collection face, when applicable, supplies Layout
metrics; PNG receives the matching file with renderer-wide system fallback
disabled. A selected face must support each numeric-spacing mode the Theme
actually requests; unsupported tabular figures are never simulated.

<!-- chrona:doc-check skip: requires a host with the Theme's installed face and fontconfig bridge -->
```sh
chrona render project.yaml --view view.yaml --theme theme.yaml --scheme scheme.yaml \
  --layout layout.yaml --system-fonts --format png --output private-review.png
```

The host bridge is `fc-match` from fontconfig. Install it with
`brew install fontconfig` on macOS, your distribution's fontconfig package on
Linux, or a fontconfig installation on Windows. A missing bridge, absent face,
or mismatched face reports `E_FONT_SYSTEM_UNAVAILABLE`,
`E_FONT_SYSTEM_MISSING`, or `E_FONT_SYSTEM_MISMATCH`; it never substitutes.
Draft system fonts support SVG and PNG only. PDF, Typst, TikZ, immutable
`render-review`, Context serialization, and `materialize` reject this volatile
state with `E_FONT_SYSTEM_IMMUTABLE`. The emitted image may be shared, but the
host path and font-resolution state are not written to Scene provenance.

## Bring your own pair

Create a local, explicit font closure with the authoring-only importer. It
validates the selected face, writes metrics from the exact persisted font bytes,
and creates/updates `font-metrics.yaml` in the output directory. The generated
names use a portable slug, and an existing family/weight is refused rather than
replaced.

<!-- chrona:doc-check skip: requires an author-provided licensed variable font -->
```sh
chrona font import fonts/acme-vf.ttf --family "Acme Sans" --weight 400 \
  --axis wght=400 --output fonts
```

For a TrueType Collection, select its zero-based face explicitly:

<!-- chrona:doc-check skip: requires an author-provided licensed TrueType Collection -->
```sh
chrona font import fonts/acme.ttc --index 2 --family "Acme Sans" --weight 700 \
  --output fonts
```

The command is local-only: it neither installs a provider nor modifies an
existing corpus/package. It accepts TTF, OTF, and TTC input that fontTools can
validate; a variable selection is serialized as a static face. Use the output
descriptor directly for draft rendering, or copy its three declared files into
an explicitly owned Context closure.

The low-level metrics tool remains useful for controlled build pipelines. For
variable fonts, instantiate the selected weight before measurement:

```sh
python tools/generate_font_metrics.py fonts/acme-vf.ttf fonts/acme-regular.metrics.json \
  --family "Acme Sans" --weight 400 --axis wght=400
```

For a non-evidence draft render, put the descriptor above in `fonts.yaml` and
pass it explicitly. Asset paths resolve relative to that descriptor:

<!-- chrona:doc-check skip: requires author-provided draft Project and presentation resources -->
```sh
chrona render project.yaml --view view.yaml --theme theme.yaml --scheme scheme.yaml \
  --layout layout.yaml --font-metrics fonts.yaml --output review.svg
```

Declare every weight selected by the Theme. A font identity is part of PNG/PDF
adapter identity, `resvg` receives only declared `font_files` with system fonts
disabled, and ReportLab receives the same declared TTF files.
