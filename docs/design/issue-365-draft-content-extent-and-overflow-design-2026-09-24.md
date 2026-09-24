# Issue 365: Draft content extent and actionable overflow design

## Decision

Chrona keeps an immutable Render Context's viewport finite and evidence-bound.
It adds a Draft-only block-axis request, `WIDTHxauto`, which Layout resolves to
a finite content extent before Scene composition or output adaptation.  The
resolved value is not written back to a Context and is not evidence suitable
for materialization.

`layoutIntent.compactness` is removed.  It has no operational consumer and
therefore cannot truthfully express a fit policy.  A future density policy
must be a separately designed, measured Layout policy; it must not silently
reuse this inert View field.

## Draft viewport contract

The CLI grammar accepts `WIDTHxHEIGHT` or `WIDTHxauto` for `chrona render`
and `chrona render-guided`.  Explicit Draft APIs carry the same distinction as
a typed Draft viewport request rather than admitting a string or `auto` into
`RenderEnvironment`.  Context schema and `RenderEnvironment` continue to
require positive finite integer dimensions.

After projection, source measurement, and Layout profile resolution, the
render use case asks Layout to resolve the Draft request.  For a fixed request
it returns the supplied extent.  For `auto`, Layout arranges the profile at a
finite seed extent and derives the extra block extent required by the measured
table/timeline content.  The returned viewport is finite, deterministic, and
is then used consistently for final layout, placement, Scene projection, and
the renderer.  No Scene, renderer, or output adapter may determine canvas
size.

The first implementation deliberately covers the table-timeline surface.  A
surface that has no declared content-extent resolver rejects `auto` with a
stable Draft diagnostic rather than inventing an adapter-local policy.

## Overflow diagnostic

`E_LAYOUT_REQUIRED_OVERFLOW` remains the stable diagnostic ID.  Each producer
adds a cause-specific detail when it has numeric facts.  The table-timeline
row failure reports the required and available block extents, row count,
minimum row/track extent, and an exact fixed viewport hint, for example:

`timeline requires 3780px for 50 rows at 72px per row; available 900px; use --viewport 1600x3780 or select fewer rows`

Generic slot, flow, alignment, and visual failures retain their own source
path and add facts only when those facts are meaningful.  Detail must survive
Layout -> Scene -> render-use-case -> CLI conversion unchanged.

## Public scale evidence

The public curriculum documents deterministic 30-row and 100-row Draft cases,
and the integration curriculum constructs and renders those cases from
declared Project/View inputs.  The 30-row case is rendered under a fixed
adequate viewport; the 100-row case exercises `WIDTHxauto` and asserts its
resolved height and successful output.  This makes the draft policy
discoverable without imposing a giant checked-in gallery artifact.

## Non-goals

This change does not paginate PDF, shrink row geometry, change Theme tokens,
or make an immutable Context adaptive.  Pagination remains a later explicit
rows/surface design.
