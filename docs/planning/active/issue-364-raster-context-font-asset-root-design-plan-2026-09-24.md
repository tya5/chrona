# Issue #364 — Raster Context-Font Asset Root Design Plan

## Problem and public basis

At public `main` `77cd55f`, a draft descriptor produced by `chrona font
import` resolves `provider: context` metrics correctly, but PNG/PDF fails when
the renderer was constructed without the descriptor's asset root. The defect is
not font import, font metrics, or adapter font loading: it is duplicate adapter
construction at the CLI/use-case boundary. Materialization has the same
uncovered shape after it rewrites provider locators to `context`.

## Design questions

1. Which layer resolves a descriptor-relative asset root for both Layout
   metrics and target-local raster bytes?
2. How can injected renderers remain a focused test seam without letting CLI
   own ordinary adapter construction?
3. How does a materialized raster Context use its rewritten snapshot root
   without a parallel special case?

## Required design work

1. Review `RenderRequest`, `render_review`, CLI draft/guided/review commands,
   materialization, and renderer registry against the Context → Layout → Scene
   → adapter direction.
2. Define one resolved `asset_root` inside `render_review`; use that value for
   metric resolution and construction of the default target adapter.
3. Keep `RenderRequest.renderer` solely as an explicit injected test/host
   adapter. Public CLI and materializer must not construct the ordinary adapter.
4. Specify acceptance tests for imported local fonts through public CLI PNG and
   PDF, and for materialized Context-relative raster font bytes.
5. Record that this changes no font policy, identity, scene geometry, locator
   syntax, or compatibility contract.

## Publication sequence

Publish this plan, then the design and whole-architecture review, then a
separate implementation plan. Implement only the accepted plan; publish the
implementation and final acceptance review after focused tests, full suite,
materializer checks, wheel smoke, and three-OS CI.
