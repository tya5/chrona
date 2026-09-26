# Design plan — as-of label placement closure (#458)

## Published baseline and scope

At `8eedb89e`, Layout creates an as-of label request with `suppress` overflow,
records a suppressed placement at the origin when no candidate fits, and Scene
emits that placement whenever the as-of line exists. The committed HALCYON 04
and 07 Scenes and SVGs show the label at `(0, 0)` despite
`W_LAYOUT_LABEL_SUPPRESSED:as-of-label`. The issue and #454 are the public work
order. No unpublished work is assumed.

## Literal issue acceptance

- On `04-tvac-slip` and `07-replan-baseline`, the as-of label is beside its line.
- No committed Scene contains a primitive recorded as suppressed.

The proposal also asks the #446 Scene gate to reject suppressed primitive IDs
and text at the canvas origin unless its slot starts there. Review whether an
origin heuristic is sound for legitimate layouts before adopting that check.

## Design questions and slices

1. Define whether as-of belongs to the timeline's declared visible-overflow
   policy, and how its placement receives the preferred beside-line coordinate.
2. Define a general suppressed-placement invariant between Layout and Scene,
   including the identity carried by diagnostics and any gate limitation.
3. Review against #449 fit policy, #446 perceptibility, Scene serialization,
   public materializers, and actual adapter output. Preserve source identity.
4. Publish design, normative correction if needed, and architecture review.
   Then publish a slice-based implementation plan before product code.

## Evidence and migration

Focused Layout/Scene fixtures, a gate fixture, both rendered HALCYON SVGs,
all committed Scene suppression checks, public materializer byte differences,
conformance and CI are required. Intended output migration is only the two
labels' placement and related diagnostics; unexpected changes require review.
