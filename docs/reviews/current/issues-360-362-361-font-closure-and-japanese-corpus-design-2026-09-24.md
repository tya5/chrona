# Issues #360, #362, and #361 — Font Closure and Japanese Corpus Design

**Decision:** Accepted.

## Decision summary

Chrona keeps an identity-pinned **metric closure** for every selected face.
Font outlines are a separate, target-local capability: SVG needs no font bytes;
PNG and PDF do.  The primary `chrona` distribution carries a small OFL Latin
default pair and its descriptor.  Japanese support is an independently
versioned OFL resource distribution installed by `chrona[fonts-cjk]`.

This is a clean migration to `chrona/render-context/v0.14`; v0.13 has no
runtime compatibility reader.  All committed Contexts migrate atomically.

## Font assets and package boundary (#360)

### Primary default

The primary wheel packages Noto Sans Regular (400) and Bold (700), their
generated metrics, OFL notice, and this descriptor:

```yaml
algorithm: declared-metrics-v2
missingFont: diagnose
assets:
  - family: Noto Sans
    weight: 400
    metrics:
      locator: {provider: package, identity: chrona.resources, address: font_metrics/noto-sans-regular-v1.json}
      contentIdentity: sha256:<metrics>
    font:
      locator: {provider: package, identity: chrona.resources, address: fonts/noto-sans-regular-v1.ttf}
      contentIdentity: sha256:<font>
```

The descriptor is a packaged data file.  The draft-default loader reads it
through the generic font-resource resolver; no product module names a family,
weight, or asset filename.  The primary build has an installed-wheel size gate
of less than 5 MB.

Theme `fontFamily` remains the CSS font-family stack.  Public Latin themes use
`Noto Sans, sans-serif`; Layout measures the first declared face in that stack
and SVG serializes the whole exact string.  Thus the declared measured face is
first while a browser without it receives an explicit generic sans-serif
fallback.  No renderer chooses or measures the fallback.

### Optional CJK provider

`chrona-fonts-noto-cjk` is a separately buildable and publishable Python
distribution in `packages/chrona-fonts-noto-cjk/`.  Its import package is
`chrona_fonts_noto_cjk`; it exposes one `chrona.font-resource-provider` entry
point whose immutable provider identity is `chrona-fonts-noto-cjk`.  The entry
point supplies a resource root only.  It does not participate in Layout,
Scene, rendering, or schema parsing.

The provider packages the JP-only Noto Sans JP source and the selected 400/700
static faces generated from it without CFF-to-glyf expansion, their metric
tables, descriptor, and OFL notice.  Each face is selected by a content
identity; the release manifest records upstream source/version, selected axis,
generated identity, and license.  The primary project declares
`fonts-cjk = ["chrona-fonts-noto-cjk==0.1.0a0"]`.  Release automation publishes
the provider before the primary distribution of the same release version.
Local CI builds and installs that subproject explicitly before testing CJK
evidence; it never relies on an unpublished index package.

An asset locator is one of:

```yaml
locator: {provider: context, address: fonts/acme-regular.ttf}
locator: {provider: package, identity: chrona.resources, address: fonts/noto-sans-regular-v1.ttf}
locator: {provider: package, identity: chrona-fonts-noto-cjk, address: fonts/noto-sans-jp-regular-v1.ttf}
```

`context` resolves below the declared asset root.  `package` resolves via the
registered provider entry point and a safe relative address.  Every read is
identity-verified.  Unknown providers, unsafe paths, missing payloads, and
identity mismatches remain closure failures; no host directories, environment
variables, or network access are consulted.

## Context and runtime ownership (#362)

`declared-metrics-v2` has required `metrics` records and optional `font`
records.  Each record is a locator plus SHA-256 identity.  A metrics table
always retains its existing `sourceContentIdentity`: the identity of the exact
font bytes from which it was generated, whether or not those bytes travel in
the Context.  When a byte record is present its identity must equal that value.
Duplicate family/weight pairs and inconsistent metric/byte source identities
are schema or closure errors.

The resolver returns two distinct values:

- `ResolvedFontMetrics` is complete after metrics identity verification and is
  the only font value passed to Layout.  It supplies advances, baseline, cap
  height, family, and source identity.
- `ResolvedRasterFont` is requested only by PNG/PDF adapters.  It resolves the
  optional byte record, verifies it, and contributes its identity to adapter
  identity.  Its absence produces `E_FONT_METRICS_UNAVAILABLE` with the
  declared byte locator path in the public detail.

Scene receives already measured text placements and never receives a resolver,
metrics descriptor, byte locator, or font path.  SVG remains a pure completed
Scene serializer.  PNG/PDF retain `skip_system_fonts=True` / explicitly
registered fonts and cannot infer a system fallback.

The target rule is consequently exact:

| Target | Metric closure | Byte closure |
| --- | --- | --- |
| SVG | required | not read or required |
| PNG/PDF | required | required for every selected rasterized face |
| Typst/TikZ | deferred; no policy change in this programme | deferred |

Public materialization accepts `missingFont: diagnose` only.  It copies all
metric files needed to resolve its Context into the snapshot, rewrites copied
locators to `context`, and copies byte files only if the Context target is PNG
or PDF.  It applies identical validation to local and provider assets.  The
materialized closure therefore has no dependency on an installed provider at
reproduction time, while an SVG snapshot can legally omit outline bytes.

## Draft substitution

`missingFont` becomes the closed enum `diagnose | substitute`; `substitute` is
admitted only by draft ingress.  It is rejected when parsing an immutable
Render Context and by the public materializer before copying any asset.

When a draft face lacks a glyph, `ResolvedFontMetrics` measures that glyph from
the packaged primary default face at the same requested weight.  It records one
deduplicated `W_FONT_GLYPH_SUBSTITUTED` warning per `(requested family, weight,
codepoint, text)` with those values and the fallback family.  Missing metrics,
malformed assets, or a missing glyph in the fallback remain hard errors.  A
`RenderedReview` carries immutable warnings; draft CLI writes canonical JSON
warning records to stderr after the output is written.  Success remains exit
code zero.  This makes substitution observable without turning a warning into
a scheduler, Scene, or renderer policy.

## Font importer (#360)

`chrona font import INPUT --family FAMILY --weight WEIGHT --output DIRECTORY`
is an authoring ingress command analogous to icon-catalog import.  `--index`
selects a TTC face and repeatable `--axis NAME=VALUE` values select/instantiate
a variable face.  The command:

1. validates the input through fontTools and resolves the requested face;
2. copies a static TTF unchanged when already static, or writes a deterministic
   selected static instance when axes are supplied;
3. generates the metrics JSON from exactly those output bytes;
4. writes collision-safe slugged face/metrics filenames; and
5. creates or atomically updates `font-metrics.yaml` with `context` locators
   and computed identities.

It refuses an existing non-identical family/weight entry rather than silently
replacing it.  It does not copy a font into an existing corpus or package.
The guide explains that a private licensed font may be used for a user's own
PNG/PDF and metrics-only SVG sharing, while anything committed or distributed
must permit that redistribution; public defaults/examples use OFL assets.

## Japanese corpus and gallery (#361)

`examples/controller-z-ja/` is a translated Controller Z register, not a new
semantic model.  It has its own project/view resources only where Japanese
content is required, a `ja-JP` Context, and a CJK-provider descriptor for
`Noto Sans JP, sans-serif`.  The board includes long title/table/axis/inside
label text so existing allocation, wrapping, and label-placement policies are
visible in published evidence.

Its manifest declares SVG evidence as the portable baseline.  A PNG/PDF
variant is declared only in an execution environment that installs the CJK
extra; both run through the same public materializer and keep their generated
evidence separate by target.  The inventory and CI make this requirement
explicit rather than silently skipping it.  The gallery contains the set as an
appearance typography comparison if its paired semantic references meet the
existing one-axis validator; otherwise it remains a documented deferred item
with the concrete missing peer.  Gallery tooling only links committed SVG and
normalized reference differences.

## Whole-architecture review

The design preserves the product's flow:

```text
descriptor/provider -> Context closure -> Layout metrics -> completed Scene
                                                     -> SVG serializer
                                                     -> PNG/PDF byte adapters
materializer -> copied, rewritten closure -> the same flow
corpus SVG -> read-only gallery documentation
```

Package discovery is an ingress/resource concern, not a rendering feature.
Metrics stay the sole geometry authority; no Scene or adapter path chooses text
coordinates.  Byte resolution is target-local and does not give a renderer
access to Theme, Context files, or host fonts.  Draft leniency is represented
as an explicit ingress policy and warning ledger; immutable evidence remains
strict.  The gallery remains downstream of committed evidence.  These choices
avoid a CJK exception, preserve offline/identity-pinned reproduction, and keep
licensing-sensitive bytes out of metrics-only SVG snapshots.

## Migration and acceptance

All public themes migrate from `Noto Sans CJK JP` to a stack whose first face
is declared by the selected descriptor.  All Contexts migrate together to
v0.14/locator records; no v0.13 reader is retained.  Generated SVGs regenerate
once after the Latin-default migration and are reviewed as one batch.

Acceptance requires provider and primary installed-wheel smoke tests, primary
wheel size below 5 MB, generic SVG family fallback, SVG metrics-only success,
PNG/PDF missing-byte rejection, substitute-warning and materializer-rejection
tests, importer fixture tests including TTC/axis paths, CJK Japanese materializer
evidence, full corpus reproduction, all structural/conformance tests, full
pytest, and Ubuntu/macOS/Windows CI with the optional provider installed for
the CJK matrix.
