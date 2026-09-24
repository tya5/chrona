# Implementation Plan: Font Distribution Integrity (#373, #380)

**Status:** Proposed

**Implements:** [Font distribution integrity design](../../design/issues-373-380-font-distribution-integrity-design-2026-09-25.md)

## I373-1 — Descriptor-owned fallback and target-honest warnings

Remove the core fallback-family literal by deriving it from the packaged
substitute descriptor.  Keep `FontGlyphSubstitution` target-neutral and add
the RenderReview-owned output-warning projection.  Extend CLI JSON tests for
the optional `drawn: false` raster/PDF fact and SVG omission.

**Files:** `src/chrona/presentation/model/font_metrics.py`,
`src/chrona/usecases/render_review.py`, `src/chrona/app/cli.py`, focused
model/use-case/CLI tests, diagnostic inventory if generated output changes.

**Acceptance:** no forbidden font literal remains in product modules; layout
substitution remains deduplicated and strict outside draft ingress; PNG/PDF
warnings state `drawn: false`; SVG makes no host/browser draw claim; immutable
materialization rejection remains unchanged.

**Publication:** focused tests and public materializer regression before one
implementation commit.

## I373-2 — Primary package truth and wheel budget

Remove the unresolved `fonts-cjk` root extra.  Document explicit local provider
installation, add availability guards only around provider-dependent tests,
and retain explicit provider installation in CI.  Add a standalone primary
wheel-size checker with the 5,000,000-byte limit and invoke it after wheel
build locally/CI before installed-wheel smoke.

**Files:** root `pyproject.toml`, `.github/workflows/conformance.yml`,
`tools/` wheel-size checker and tests, CJK-specific tests, font guide,
wheel/release checks and any generated inventories.

**Acceptance:** a plain primary editable install followed by the full suite is
green with stated CJK skips; the CI/provider path still runs CJK evidence;
the primary wheel passes below the limit; a synthetic over-limit wheel fails
with a stable actionable message.

**Publication:** focused plain/provider environment evidence and wheel smoke
before one implementation commit.

## I380-1 — Reproducible provider build and metadata correction

Add the offline provider-build tool and provenance record.  It accepts explicit
Source Han Sans 2.004 source-face/notice inputs, produces the 400/700 static
provider artifacts, copies the supplied upstream notice, rewrites all required
name records, preserves copyright/license/manufacturer and OS/2 weight, and
regenerates metrics and descriptor identities.  Add focused generator/name/
notice/provenance tests.

**Files:** a dedicated `tools/` provider-build module, provider source assets
and provenance record, provider descriptor/metrics/fonts/notice, focused tool
and provider-resource tests, documentation where source provenance is exposed.

**Acceptance:** no output uses Source as a family/unique/PostScript name;
regular/bold name records and 400/700 weights agree with the descriptor; the
notice is byte-copied from the supplied official 2.004 notice; source/input and
generated identities are recorded; an input/output collision is rejected.

**Publication:** implementation and generated provider asset review in one
atomic commit; never commit a hand-edited binary or identity.

## I380-2 — Japanese corpus closure regeneration

Synchronize the provider descriptor into the provider-dependent
`controller-z-ja` Context with the deterministic font-closure synchronizer,
then regenerate SVG only through the public materializer using the corrected
provider.  Review all identity and SVG differences, then prove SVG/PNG/PDF
with the local provider.

**Files:** deterministic font-closure synchronizer and tests,
`examples/controller-z-ja/` Context/resources/generated evidence,
corpus/inventory checks, CJK target tests, generated documentation if changed.

**Acceptance:** the synchronizer changes only the Context font closure and
pins corrected provider identities; committed SVG
matches public materialization byte-for-byte; Japanese SVG/PNG/PDF still
render from declared bytes; no unrelated corpus SVG changes occur.

**Publication:** a separate generated-evidence commit after diff review.

## Release gate

After all slices: run each focused suite; plain-primary and explicit-provider
installation checks; primary/provider wheel build and size checks; installed
wheel smoke; all public materializers and generated SVG diff review;
conformance; documented-command, reachability, primitive-delivery, dispatch,
import-direction, text-encoding, diagnostic and declared-value checks; full
parallel pytest; then Ubuntu/macOS/Windows CI.  Publish a release review with
the exact artifacts and CI run before closing #373 and #380.
