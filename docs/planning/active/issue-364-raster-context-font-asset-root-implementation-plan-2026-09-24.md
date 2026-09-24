# Issue #364 — Raster Context-Font Asset Root Implementation Plan

## I364-1 — Single default-adapter construction path

**Files:** `src/chrona/app/cli.py`, `src/chrona/usecases/render_review.py`.

**Work:** remove ordinary renderer construction from the CLI helper. In
`render_review`, pass the already-computed effective asset root to
`renderer_for` when no renderer is explicitly injected.

**Acceptance:** a draft Context-relative descriptor resolves the same root for
metrics and PNG/PDF font bytes; injected renderers retain their explicit seam;
SVG output does not change.

## I364-2 — Target-local closure regression tests

**Files:** CLI tests, renderer/use-case tests, materializer integration tests.

**Work:** use a local descriptor/fixture through the public CLI for PNG and
PDF, assert target signatures and imported font identity in adapter identity,
and test a copied/re-written materialized Context directly through
`RenderRequest` without a pre-built renderer.

**Acceptance:** no host font is used; a missing local raster byte continues to
diagnose; the materialized snapshot root supplies rewritten font records.

## I364-3 — Verification and publication

Run focused tests, full pytest, conformance, structural checks, all declared
materializers, generated SVG diff review, primary installed-wheel smoke, and
the three-OS CI matrix. Publish a release review and close #364 only after the
final remote `main` CI succeeds.
