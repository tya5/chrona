# Issue #364 — Raster Context-Font Asset Root Design

## Decision

`render_review` is the sole owner of ordinary renderer construction. It derives
one effective asset root from `RenderRequest.asset_root`, or from the resolved
Context snapshot/theme revision when that explicit root is absent. It passes
that same effective root to both `resolve_font_metrics` and `renderer_for`.

`RenderRequest.renderer` remains an explicit injection seam for unit tests or
an embedding host. It is not used by public CLI or materialization. Thus an
injected renderer keeps its own dependencies by explicit construction, while
the normal application path cannot split metric and outline resolution.

## Responsibility review

```text
CLI / materializer -> RenderRequest (closure, optional explicit asset root)
                         -> render_review resolves effective asset root
                              -> Layout metrics
                              -> completed Scene
                              -> default target adapter / raster font bytes
```

This keeps Context-relative locator resolution at the application closure
boundary. Layout remains the only geometry authority. Scene receives measured,
completed placements and has no resource lookup. PNG/PDF adapters receive only
their target-local, identity-verified font files; they neither discover Context
files nor select a root themselves.

For a materialized Context, the request carries no explicit root, so the same
fallback resolves the rewritten files under the snapshot revision directory.
For a draft descriptor, closure ingress supplies its descriptor directory as
the explicit root. Package locators remain independent of that root.

## Consequences

- `app.cli._render_review` stops pre-building a renderer.
- The default branch in `render_review` uses the already-derived effective root
  rather than the raw optional request field.
- No schema, locator, font policy, artifact identity, Scene, or public command
  syntax changes.
- The prior behavior that an explicitly injected renderer owns its dependencies
  is retained intentionally; it is a test/host seam, not an ordinary path.

## Acceptance

1. A CLI draft using an importer-created local descriptor renders PNG and PDF,
   and each artifact identity includes the imported font identity.
2. SVG behavior remains metrics-only and unchanged.
3. A materialized raster Context with copied/re-written context font records
   renders successfully and verifies bytes from its snapshot root.
4. Missing/mismatched raster bytes still fail with the existing stable font
   diagnostic and locator detail.
5. Focused tests, full suite, materializers, installed-wheel smoke, and
   Ubuntu/macOS/Windows CI pass.
