# Issue 120 — Draft Render Path Design Review

## Decision

`chrona render` becomes the draft review renderer.  It accepts resource paths,
validates and freezes them through the same contract parser, synthesizes an
in-memory `RenderClosure`, and calls `render_review`.  The legacy generic
renderer is removed from this command path; immutable `render-review` remains
the reproducible Context/snapshot evidence path.

## Draft boundary

Introduce a draft-closure factory owned by presentation ingress.  It loads only
the explicitly supplied files, assigns non-evidence `draft` identities, calls
`parse_contract`, resolves the Theme against the Color Scheme, and constructs
a minimal v0.6 context contract.  It never writes a Context, snapshot, hash,
or revision artifact.  The factory also returns the packaged resource root used
for the declared default font metrics.

The CLI owns parsing paths and defaults; the use case still owns pipeline order.
No downstream stage may branch on draft versus immutable origin.

## CLI contract

```
chrona render PROJECT --view VIEW --theme THEME --scheme SCHEME --layout LAYOUT \
  [--actual ACTUAL] [--summary SUMMARY] [--detail DETAIL] \
  [--viewport WIDTHxHEIGHT] [--locale en-US] --output OUTPUT
```

The help text explicitly says this output is draft and not reproducible
evidence.  Defaults are `1600x900`, `en-US`, SVG capabilities required by the
current v0.5 renderer, and the packaged Nimbus Sans metric asset.  Invalid path,
schema, viewport, or locale input uses existing stable diagnostics.

## Whole-architecture consistency review

This keeps source ingress at contracts/closure, pipeline assembly in
`render_review`, geometry in Layout, and output serialization in the renderer.
It removes the legacy renderer from the authoring command rather than retaining
two semantic render products.  It also prepares #122: both immutable and draft
paths enter the same renderer selection seam, so format support is not copied.

## Acceptance

A draft invocation of a public example produces exactly the current review SVG;
optional inputs are read by the same ledger rules; immutable render-review bytes
remain unchanged; CLI failure cases name the bad argument/resource; no Context
or snapshot is created.
