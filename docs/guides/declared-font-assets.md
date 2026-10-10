# Declared Font Assets

Chrona measures text from the exact metrics declared by an immutable Render
Context. PNG/PDF additionally use identity-pinned font bytes; SVG does not
load them. Immutable rendering never uses a host-installed font. The bundled default is the
small OFL `Noto Sans` Regular/Bold pair. The separately distributed OFL
`Noto Sans JP` provider is installed explicitly for repository development:
`pip install -e packages/chrona-fonts-noto-cjk`. It is not advertised as a
primary-package extra until that provider is published to an installable index.

## Context closure

`chrona/render-context/v0.17` (and the still-readable v0.16) requires a metrics record for every family/weight
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

### Installed fonts are a normal source

Fonts installed on the machine are used on every render path: `chrona render`, `render-review` through a Render
Context, and SVG, PNG and PDF output. Output therefore depends on the fonts installed where it is rendered, and that
is intended: someone who owns a face and wants to design with it can, and reproducibility across machines is not a
goal of this path. Chrona ships no new fonts; declared `package` or `context` metrics keep working and take
precedence when a Theme names a declared family.

A Theme `fontFamily` is an ordered list, for example `Hiragino Sans, Yu Gothic, Noto Sans JP`:

1. Layout uses the first family that is declared by the Context's font descriptor or installed here. An installed
   face is found by family name (the typographic and the legacy name, collection files included) and the weight
   nearest the role's by the CSS font-weight rule.
2. If a character is missing from that face, the next family of the list that has it supplies it, as in a browser,
   and the packaged Noto Sans comes last. Text that no listed or packaged face covers fails with
   `E_FONT_GLYPH_UNAVAILABLE` naming the character and the faces tried.
3. If no listed family is declared or installed, the role uses the packaged Noto Sans at the role's weight. CSS
   generic names (`sans-serif`, `monospace`) end a list and are not resolved.

The Scene records the face each role resolved to (`textLayout.family`), and the render reports one note per role whose
list was resolved: `I_FONT_ROLE_RESOLVED:role=...;requested=<list>;face=<family>`, or the warning
`W_FONT_FALLBACK_PACKAGED:role=...;requested=<list>;face=Noto Sans` when it fell back. SVG names the resolved family
and embeds nothing; PNG and PDF rasterize with the resolved files (the PDF adapter embeds TrueType outlines only: an installed
face with PostScript outlines, such as the macOS Hiragino collections, is refused for PDF with `E_RENDER_FONT_CLOSURE` naming the
face, and renders to SVG and PNG). A selected face must support each numeric-spacing
mode the Theme requests: unsupported tabular figures are never simulated (the role degrades to proportional and
says so).

No fontconfig is needed. Chrona scans the standard font directories and reads each file's family and weight with
fontTools: macOS `/System/Library/Fonts`, `/Library/Fonts` and `~/Library/Fonts`; Windows `%WINDIR%\Fonts` and
`%LOCALAPPDATA%\Microsoft\Windows\Fonts`; Linux fontconfig's file list when `fc-list` is present, else the XDG
font directories. `CHRONA_FONT_PATH` adds directories (separated like `PATH`). The index is built once per process.

`--system-fonts` is still accepted. It asks for the stricter exact-face lookup through fontconfig's `fc-match` (a
missing face is `E_FONT_SYSTEM_MISSING`, not a fallback) and is no longer limited to SVG and PNG.

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
