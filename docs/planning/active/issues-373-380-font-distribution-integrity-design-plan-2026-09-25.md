# Design Plan: Font Distribution Integrity (#373, #380)

**Status:** Proposed

## Purpose

Complete the residual work from the font-closure programme without weakening
its architecture.  #373 concerns the primary wheel, draft-only diagnostics,
and optional development/provider boundaries.  #380 concerns the independent
Japanese provider's legal notice and static-face metadata.  They are planned
together because both are distribution-integrity work, not Layout or renderer
feature work.

## Verified starting facts

1. `font_metrics.py` still passes a hard-coded fallback family despite the
   packaged substitute descriptor already declaring that family.
2. The CI builds a primary wheel but contains no machine-enforced primary-wheel
   size limit.
3. The root `fonts-cjk` extra names `chrona-fonts-noto-cjk==0.1.0a0`, while
   that distribution is not published.  The CI correctly installs the local
   provider explicitly, but a plain editable primary checkout leaves direct
   CJK tests unguarded.
4. A `FontGlyphSubstitution` is a target-neutral metric event.  Raster/PDF
   output, however, has no fallback outlines and must not describe a measured
   substitution as a drawn glyph.
5. The provider faces identify Source Han Sans 2.004 in their name records:
   copyright and Reserved Font Name belong to Adobe, while both installed
   artifacts are currently named `Noto Sans JP Thin` regardless of their
   400/700 `OS/2.usWeightClass`.
6. The authoritative Source Han Sans 2.004 upstream notice names Adobe and
   the Reserved Font Name `Source`; the provider's copied Latin Noto notice is
   therefore not a valid notice for these artifacts.

## Design questions and required decisions

1. Define the data-owned substitute-family lookup so product code names no
   font family, weight, or asset filename.
2. Define a CI-owned primary-wheel size gate: its threshold, wheel selection,
   failure message, and why the CJK provider is deliberately out of scope.
3. Define truthful provider availability: remove an unresolved public extra
   until a provider is actually published; specify the supported local
   development installation and optional-test behavior without making CJK
   evidence disappear from CI.
4. Separate target-neutral measurement substitutions from target-specific
   output warnings.  Specify exactly which target may report `drawn: false`,
   where the projection happens, and the stable JSON contract.
5. Define a reproducible provider-build input/output contract: pinned Source
   Han Sans source and notice inputs, deterministic static-face instantiation,
   name-table rewrite policy, metric regeneration, descriptor identity update,
   and the Japanese corpus regeneration boundary.
6. Confirm the change preserves the established flow:

   ```text
   provider/build inputs -> resource provider -> font closure -> Layout metrics
                                                        -> completed Scene
                                                        -> target adapter
   metric substitution ledger -> RenderReview warning projection -> CLI JSON
   ```

   No layout, Scene, renderer, Context, or materializer may acquire provider
   build, licensing, or host-font responsibility.

## Design deliverables

- An English design defining the provider/build, warning, package, and CI
  boundaries, including rejected alternatives and migration impact.
- A whole-architecture review against the existing font-closure design.
- An implementation plan divided into independently reviewable publication
  slices with files, focused acceptance, full release gates, and generated
  Japanese-corpus evidence.

## Evidence required before implementation

- Inspect current name tables and `OS/2` weights for both provider faces.
- Verify the exact upstream notice against the Source Han Sans 2.004 source
  identified by the artifacts, rather than copying a current or unrelated
  Noto notice.
- Establish current primary-wheel compressed size and a deliberate threshold.
- Demonstrate the plain editable primary install behavior separately from the
  CI's explicit local-provider install.
- Characterize SVG, PNG, and PDF substitution warnings and their output.

## Publication order

1. Publish this plan.
2. Publish the accepted design and architecture review.
3. Publish the implementation plan.
4. Implement/provider-regenerate in the planned atomic slices, with focused
   checks after each.
5. Publish a release review after full tests, public materializers, wheel
   checks, generated SVG review, and Ubuntu/macOS/Windows CI; only then close
   #373 and #380.
