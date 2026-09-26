# Design Correction — Painted Sample and Hosted Marks (#459)

The first implementation probe, run against the 21 committed Scenes after
the [initial design](issue-459-surface-aware-contrast-design-2026-09-26.md),
exposed 954 below-floor/invalid-treatment findings. This is diagnostic
evidence, not an accepted release: no #459 product code was published.

## Corrected sample contract

The initial bounds-centre rule is valid for flat-filled Rects and Text, but
not for a stroke-only Rect: its centre is unpainted. For a stroke-only Rect,
sample the left edge at the block midpoint (or top edge at the inline
midpoint when its width is zero). The same paint-order ground search is then
performed at that point. A completed stroke-width is required for this form.
The Scene finding records `sampleInline`, `sampleBlock`, and the channel, so a
reviewer can distinguish a painted edge from a bounds-centre estimate.

For a Symbol, the bounds centre is a finite approximation of its completed
outline; its fill/stroke channel still determines visibility. A future exact
contour evaluator may refine this, but it may not silently reclassify an
unpainted point as the rendered mark. Unsupported non-flat/transparent hosts
remain explicit diagnostics, not canvas fallbacks.

## Hosted submarks are independently visible

The probe found `progress-fill` often almost identical to its earlier actual
host (1.016:1 in the published orion Scene). It remains in the data-mark
class. The fact that it is an overlay does not exempt it: its purpose is to
visibly encode progress, so the 3.0:1 floor applies against the actual host.
Likewise `missing-actual` and `network-node` remain classified. The resource
migration must repair those paints instead of narrowing the policy to make
the report pass. Stroke-only calendar decorations also need their actual
surface ground, even though this expands #431's earlier corpus migration.

## Whole-architecture consistency

Geometry and paint order are completed Scene facts. Theme/Scheme continue to
own colour choices, and the pure Scene observer only samples them. No adapter
is asked to infer a ground or choose a repair colour. The correction preserves
Specification 46 and the #431 finite role-policy boundary while replacing
its canvas assumption for classified primitives. The public materializer
must migrate all affected surfaces atomically; a red intermediate checker is
not a valid publication boundary.
