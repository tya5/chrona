# Design Correction: Completed Icon Paths at the Scene Boundary (#350)

**Status:** Design complete — required to complete I350R-5.

## Finding

The current SVG adapter serializes normalized icon paths but still interprets
their paint mode, stroke width, cap, join, and Layout stroke scale from
`NormalizedVectorIcon` and `ScenePrimitive`. This leaves renderer-owned
semantics after the Layout-to-Scene handoff, contrary to the successor plan's
completed per-path payload.

## Corrected contract

Layout retains geometric scaling and emits a closed icon placement. Scene
projects it into immutable renderer-neutral `SceneIconPath` values. Each path
contains final commands plus final fill/stroke channels, width, cap, join, and
opacity derived from the primitive's already-completed semantic paint and the
Layout stroke scale. The Scene primitive carries only these completed paths,
not a normalizer model or a scale for adapters to apply.

The SVG adapter serializes those fields verbatim. It does not import icon
normalization, Theme tokens, Layout values, or choose fill versus stroke.
Raster icon bytes remain an independently closed payload.

## Architecture consistency review

Catalog ingress owns normalization and safety validation. Layout owns icon
geometry and stroke scale. Scene owns the one projection from completed
placement plus semantic paint to adapter-neutral icon paths. Renderers only
serialize. This preserves color authority in Theme/Scene while eliminating the
last adapter-side visual policy.

## Implementation and acceptance plan

1. Introduce an immutable completed Scene icon-path model and replace vector
   normalizer payload/scale fields on `ScenePrimitive`.
2. Project every Layout vector icon path through completed primitive paint and
   Layout scale; reject invalid combinations before adapters run.
3. Simplify SVG serialization to consume only Scene icon paths; add structural
   tests that reject normalizer/Layout imports in the adapter.
4. Prove fill and stroke path byte output, label/mark paint distinction,
   raster behavior, accessibility, unsupported-target rejection, public
   materializers, and full suite.
