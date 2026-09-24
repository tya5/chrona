# Issues #360, #362, and #361 — Font Closure and Japanese Corpus Implementation Plan

**Status:** Proposed

## Governing design

This plan implements the accepted font-closure design and its architecture
review.  The public sequence is #360, then #362, then #361.  No compatibility
reader for Render Context v0.13 is retained: every committed Context migrates
in the atomic schema slice.

## I360-1 — Provider-neutral metric closure contract

**Scope:** introduce Render Context v0.14, safe local/package asset locators,
and independent metric/byte resolution.

**Files:** `schemas/render-context-v0.14.schema.yaml`, schema inventory and
typed contract records, `presentation/model/font_metrics.py`,
`presentation/model/closure.py`, resource-provider module, resolver tests,
schema tests, closure tests, and structural tests.

**Work:**

1. Add the closed `context | package` locator record, provider registration,
   safe traversal and identity checks.  Register the primary resource provider
   without naming any particular font asset.
2. Make metric records required and byte records optional; retain and validate
   metric `sourceContentIdentity`.  Split `ResolvedFontMetrics` from
   `ResolvedRasterFont` and route target-specific byte loading only through
   PNG/PDF adapter entry points.
3. Advance Context/schema/typed parsing atomically to v0.14 and migrate every
   committed Context to locator syntax.  Reject v0.13 rather than maintaining
   an alternate closure path.

**Focused acceptance:** a local and a package metrics record resolve; unsafe,
unknown, absent, and identity-mismatched locators reject; SVG resolution
succeeds without a font payload; raster resolution rejects a missing font
payload with stable path detail; Scene imports no font resolver.

**Publication:** schema/closure commit and focused test evidence.

## I360-2 — Primary default and optional CJK distribution

**Scope:** replace primary CJK assets with the Latin default, introduce the
separate CJK provider package, descriptors, wheel sizing, and generic SVG
fallback.

**Files:** `pyproject.toml`, Hatch package-data rules,
`src/chrona/resources/fonts/`, `font_metrics/`, descriptor resources,
`packages/chrona-fonts-noto-cjk/`, notices/release manifest, package resource
tests, `closure.py` default-descriptor loader, public themes/Contexts/generated
SVGs, CI dependency/install steps, wheel-smoke and wheel-size tests.

**Work:**

1. Obtain and verify OFL sources; generate/check in the Noto Sans Latin pair
   and metrics in the primary package.  Remove the pan-CJK primary assets.
2. Build the CJK resource distribution from JP-only Noto Sans JP assets,
   descriptor and provider entry point.  Make `chrona[fonts-cjk]` declare its
   release dependency while CI builds/installs the local provider explicitly.
3. Load the primary default descriptor as data.  Migrate public themes to
   `Noto Sans, sans-serif` and CJK Contexts to `Noto Sans JP, sans-serif`.
   Regenerate every changed corpus SVG as one reviewed batch.
4. Preserve complete CSS stacks in text placements/serialization and prove the
   generic fallback appears in SVG.

**Focused acceptance:** no primary CJK TTF is present; primary wheel is below
5 MB; default draft SVG/PNG/PDF works from an installed primary wheel; provider
install resolves CJK SVG/PNG/PDF; SVG contains `Noto Sans, sans-serif`; notices
and every resource identity are verified.

**Publication:** #360 implementation/review commit only after primary and
provider wheel smoke and full corpus SVG regeneration are reviewed.

## I362-1 — Target-local byte enforcement and draft substitute policy

**Scope:** implement target admission, strict materializer copying, substitute
warnings, and licensing documentation.

**Files:** renderer registry/adapters, `render_review.py`, CLI warning emitter,
`materialize.py`, draft closure ingress, tests in model/usecase/CLI/materializer
suites, `docs/guides/declared-font-assets.md`.

**Work:**

1. Request raster bytes only in PNG/PDF adapters and preserve their identity in
   artifact identity.  SVG must never read a byte locator.
2. Add draft-only `missingFont: substitute`; make its default-face measurement
   ledger produce canonical structured `W_FONT_GLYPH_SUBSTITUTED` warnings and
   surface them on successful draft CLI rendering.
3. Reject `substitute` for immutable Context/materialization.  Copy every
   required metrics payload into snapshots, copy outlines only for PNG/PDF, and
   rewrite copied locators to local Context paths.
4. Document OFL/public-corpus and private-license boundaries.

**Focused acceptance:** metrics-only SVG works; the same descriptor rejects
PNG/PDF with `E_FONT_METRICS_UNAVAILABLE` and locator detail; draft `General
Availability ✅` succeeds with exactly one warning; strict/durable closures
reject that glyph or `substitute`; SVG snapshots omit font bytes; raster
snapshots contain verified bytes.

**Publication:** #362 implementation/review commit after focused tests and
public materializer regression checks.

## I360-3 — Deterministic font import command

**Scope:** expose the accepted private-font authoring ingress.

**Files:** `app/cli.py`, a dedicated font-import usecase/module,
`tools/generate_font_metrics.py` shared primitives as appropriate, importer
tests, CLI tests, and the declared-font guide.

**Work:** add `chrona font import` subcommands/arguments, static/TTC/axis
selection, safe slug/collision rules, atomic descriptor update, and actionable
license guidance.  Keep the command isolated from rendering/resource providers.

**Focused acceptance:** static input, TTC index, variable-axis fixture,
duplicate rejection, atomic failure preservation, generated descriptor
resolution, and Windows-safe paths all pass.

**Publication:** add to #360 only when the command is installed-wheel smoke
tested and documented; do not defer it behind the Japanese corpus.

## I361-1 — Japanese Controller Z corpus and gallery evidence

**Scope:** add the translated corpus set and its explicit target/provider
matrix after #360/#362 are merged on main.

**Files:** `examples/controller-z-ja/`, corpus manifest/inventory tests,
generated evidence, `docs/gallery/example-gallery.yaml`, generated gallery
pages, gallery tests, CI CJK matrix, and release documentation.

**Work:** create the translated Board and normal Contexts, declare the CJK
provider metric/byte locator records, generate SVG and target-specific raster
evidence, and create a valid one-axis gallery pair or retain a real deferred
entry if no valid peer exists.  Run the existing gallery generator; never hand
author its pages.

**Focused acceptance:** Japanese SVG materializes from its declared Context;
the CJK raster matrix materializes with the extra; no implicit host font is
observed; gallery provenance/reference diff validates; inventory names the
provider requirement.

**Publication:** #361 corpus/gallery commit after generated evidence review.

## Release gate

After the final slice, run focused tests during each slice and one batched
release gate: `pytest`, conformance, all structural checks, corpus inventory,
all public materializers, generated SVG diff inspection, primary/provider
installed-wheel smoke, primary wheel-size assertion, and the Ubuntu/macOS/
Windows CI matrix.  Check remote main/diff/commit range immediately before each
serial push; never force-push.  Publish a release review naming the exact CI
run and close #360, #362, and #361 only after their individual acceptance
evidence is present on GitHub.

