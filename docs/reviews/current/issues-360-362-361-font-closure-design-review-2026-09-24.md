# Issues #360, #362, and #361 — Font Closure Design Review

**Result:** Accepted with one completed correction.

## Reviewed boundaries

| Boundary | Decision | Review result |
| --- | --- | --- |
| Resource package → closure | Registered resource providers resolve identity-pinned locators. | Provider discovery does not expose package paths to Layout or adapters. |
| Context → Layout | Metrics are required and resolve independently of outline bytes. | Layout remains the sole measurement/geometry owner. |
| Scene → adapters | Scene contains completed text only; SVG serializes its declared stack; raster adapters request bytes. | No Scene font read, host fallback, or adapter coordinate policy is introduced. |
| Materializer → snapshot | Metrics always copy; bytes copy only for PNG/PDF. | Rewritten local locators leave snapshots self-contained without redistributing unnecessary bytes. |
| Draft ingress → evidence | `substitute` is draft-only with warnings. | Immutable Context parsing and materialization stay strict. |
| Corpus → gallery | Japanese SVG is ordinary corpus evidence and gallery input is read-only. | No gallery resolver or CJK fixture exception appears. |

## Correction made during review

The first design wording proposed a new `sourceFaceIdentity` for metrics-only
assets.  That would duplicate the existing metrics contract's
`sourceContentIdentity` and create two source-identity terms for the same
font.  The accepted design instead keeps `sourceContentIdentity` mandatory in
the metric file whether or not the Context distributes the corresponding font
bytes.  A present byte record must equal it.  This retains a single provenance
edge for importer output, packaged assets, metrics-only SVG sharing, and
raster validation.

## Cross-cutting findings

- A Python extra cannot alter an already-built wheel's package data.  The
  separate provider distribution is therefore necessary; treating an
  uninstalled repository directory as an extra would fail installed-wheel and
  release use cases.
- A CSS stack already has the required authority: the first declared family is
  measured and any subsequent generic family is serialization-only.  A new
  renderer token or Scene fallback mechanism would duplicate Theme authority.
- Warning transport belongs to the draft ingress/use-case result, not the
  scheduler diagnostic path.  It is neither a rejected Context nor a Scene
  concern.
- Typst/TikZ have independent text-engine contracts.  Extending the
  PNG/PDF-byte rule to them without target evidence would be an unsupported
  policy inference, so they remain out of scope.

The design is internally consistent with the immutable Context, completed
Scene, provider/resource, materializer, corpus, and gallery architecture.  It
is ready for the implementation plan.

