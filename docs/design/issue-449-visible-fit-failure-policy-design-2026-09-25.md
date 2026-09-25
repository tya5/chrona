# Design — Visible Fit and Placement Failure Policy (#449)

**Status:** proposed for architecture review.
**Supersedes:** the fit/placement refusal rule in ADR-0031 and the
refuse-on-`diagnose` portions of the #400 row-density design.

## Decision

A valid Chrona closure always produces a review artifact when only fit or
placement constraints fail.  Layout completes a visible fallback placement and
a structured warning; it does not return a fit/placement error to render
ingress.  The renderer serializes the completed result.  Invalid or
inconsistent input, missing resources, integrity/identity violations, and a
target that cannot serialize an already-completed primitive remain errors.

`diagnose` is removed from the user-facing fit/placement vocabulary.  Layout
Profile v0.9 and affected View resources use `visible-overflow` as the normal,
explicit disposition.  The already author-selected alternatives remain:
`ellipsize-with-source`, `clip-optional`, wrapping, and `thin-with-record`.
`suppress` remains available only where a View explicitly selects it; it is
never a default.  There is no compatibility reader for the retired meaning of
`diagnose`.

## Completed Layout contract

Layout owns a finite `FitWarning` record:

```text
FitWarning(
  code, placement_id, source_ref, failure_kind, behaviour,
  required_inline, required_block, available_inline, available_block
)
```

All fields are completed facts, not a request for Scene or an adapter to make a
policy decision.  `SurfacePlacement` carries ordered `FitWarning` values and a
completed `canvas_bounds`; every primitive has geometry that is inside that
canvas.  The Scene serializes the structured warnings and the completed canvas
dimensions.  The CLI emits the same ordered records to stderr after writing a
successful artifact.  Existing unstructured diagnostic strings are migrated,
not duplicated, for these failures.

The requested Context viewport becomes Layout's minimum allocation.  Layout
may deterministically enlarge `canvas_bounds` to include a visible fallback,
anchored at the requested canvas origin.  It never relies on SVG overflow CSS
or an adapter crop: SVG dimensions/viewBox, PNG raster dimensions, PDF bounds,
and typeset page/canvas dimensions all consume the completed canvas.  Thus a
fixed immutable Context remains reproducible while its artifact truthfully
records the larger completed extent.

## Failure-disposition registry

The following registry is the only fit/placement fallback authority.  The
listed warning is one per affected completed placement; its payload always
contains the applicable required and available extents.

| Failure family | Normal completed behaviour | Explicit alternative | Warning |
| --- | --- | --- | --- |
| required slot / table text | Place measured natural text; it may escape the assigned slot and expands the canvas if needed. | ellipsize, wrap, or clip when declared | `W_LAYOUT_VISIBLE_OVERFLOW` |
| review-row density | Keep P1 row requirements, tracks, marks and table cells at natural geometry; extend the review surface/canvas. | compact or row clip only through a future explicit row policy | `W_LAYOUT_ROW_DENSITY` |
| mark containment | Keep the completed mark at its natural track geometry and extend its physical host/canvas. | none in this release | `W_LAYOUT_MARK_OVERFLOW` |
| plot / annotation / relation label collision | Place the deterministic preferred candidate even when it intersects a required obstacle. | declared `suppress` only | `W_LAYOUT_LABEL_OVERFLOW` |
| axis label density | Place every declared label, including overlaps. | declared `thin-with-record` | `W_LAYOUT_AXIS_OVERFLOW` |
| relation route limit | Emit the deterministic direct endpoint path, even when it crosses obstacles or exceeds quality limits. | declared `suppress` only | `W_LAYOUT_ROUTE_FALLBACK` |
| folded group-header density | Stack every completed header/milestone placement in stable order and extend the host/canvas. | none in this release | `W_LAYOUT_GROUP_HEADER_OVERFLOW` |
| dependency-network allocation | Keep all node/edge geometry and extend the completed network/canvas bounds. | none in this release | `W_LAYOUT_NETWORK_OVERFLOW` |

Candidate rejection remains an internal Layout operation where it is followed
by the row above.  No candidate failure may escape through `RenderFailed` for
a valid closure.  A warning is not an error code reused as a success result.

## Geometry invariants

1. Every semantic item named by the closed input has a completed placement or
   an author-declared suppression record.  Default fit policy never drops an
   item.
2. Natural geometry is measured once in Layout.  Visible overflow may cross a
   slot, collision domain, track, or former viewport allocation, but not the
   completed `canvas_bounds`.
3. A compacted/clipped/ellipsized/thinned result is permitted only when its
   resource explicitly names that disposition and its source/provenance record
   remains inspectable.
4. `canvas_bounds`, fallback paths, overlap positions, and warnings are
   deterministic for the same closed input and measurement assets.
5. Scene projects placements, canvas bounds and warnings verbatim.  It does
   not measure, choose a fallback, enlarge a canvas, route a relation, or turn
   a warning into a primitive.  Adapters serialize completed values only.

## Boundary and migration

```text
Project / View / Profile / Theme + measured assets
                    |
                    v
Layout: requirements, normal placement, visible fallback,
        completed canvas and FitWarning records
                    |
                    v
Scene: verbatim primitives, canvas and warnings
                    |
                    v
SVG / PNG / PDF / Typst / TikZ: serialize completed geometry
```

The migration is one atomic v0.8 → v0.9 Layout Profile replacement together
with every live View/Profile declaration, Context closure identity, schema
inventory, generated Scene/SVG evidence, and all capability/schema tests.
The #405–#408 axis work is amended: the ordinary path places all labels; its
recorded thinning path is retained only for `thin-with-record`.  The proposed
I400-1 `rowDensity.{draft,immutable}: diagnose` contract is discarded rather
than published.

## Whole-architecture consistency review

This preserves the central ADR-0031 ownership boundary: Project and View
provide facts and declared exceptional choices; Theme supplies measurements;
Layout alone resolves physical consequences; Scene is projection; renderers
are serializers.  It changes only feasibility semantics from "valid or
refuse" to "completed and observable."  Specification 08's no-reflow rule
remains valid because canvas growth and overflow coordinates are completed
before Scene.  Specification 50's required-in-slot and non-overlap assertions
must be narrowed to policies that explicitly request those properties; its
unconditional versions conflict with this owner decision and will be amended.

## Acceptance

- Neutral fixtures cover every registry family and prove a valid closure
  produces an artifact, structured Scene warning, and CLI warning.
- Negative tests retain rejection for schema, unknown-reference, resource, and
  integrity failures.
- Structural tests prohibit fit/placement `RenderFailed` paths and prohibit
  Scene/adapters from resolving a disposition or canvas extent.
- All public materializers, all targets, full pytest, conformance, generated
  SVG/PNG review, wheel smoke, and three-platform CI pass after the atomic
  resource migration.
