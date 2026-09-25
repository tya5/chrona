# Architecture Review — Measured Typography, Orientation, and Draft Fonts

**Design reviewed:** `dafcb31f`
**Status:** accepted for implementation planning.

## Boundary review

| Boundary | Decision | Review result |
| --- | --- | --- |
| Theme -> Layout | Theme returns typed finite `TextTreatment`; it does not measure or transform content. | Pass |
| View -> Layout | View may request finite label/header orientation; it does not supply coordinates or adapter syntax. | Pass |
| Layout -> Scene | Layout supplies transformed content, occupied bounds, baseline anchor, numeric feature, and angle on a completed placement. | Pass |
| Scene -> adapter | Scene transports completed text layout; adapters serialize supplied values and cannot infer a fallback. | Pass |
| Draft -> immutable | `DraftFontResolution` remains runtime-only and nonportable; Context schemas retain only reproducible locators. | Pass |

## Key architecture findings

1. `FontMetrics.width()` already has a letter-spacing parameter, but the
   current positional typography tuple is an incomplete contract.  Replacing it
   with one typed value is necessary to prevent callers from independently
   adding a new field while forgetting a measurement consumer.
2. Text orientation is geometry, not Theme paint.  Carrying it as a Theme role
   would make paint capable of invalidating a Layout fit decision.  View intent
   plus completed Layout geometry is the correct ownership split.
3. `writingMode` combines two incompatible claims: coordinate-flow selection
   and vertical text.  The v0.8 split removes the misleading declaration rather
   than documenting a false renderer capability.
4. A `system` locator in render-context would make an ostensibly immutable
   closure host-dependent.  A draft runtime object prevents that leak and lets
   materializer paths reject nonportable provenance structurally.

## Risks and required controls

| Risk | Required control |
| --- | --- |
| Transform or tracking changes visual text after fitting | Store canonical painted content and resolved spacing in completed placement; forbid adapter transforms beyond supplied rotation. |
| Tabular feature differs from measured width | Require v3 metric support for tabular advances before the Theme may select it. |
| Rotation clips or collides as horizontal text | Fit/collision operate on swapped occupied bounds; add negative tests for the old horizontal rectangle. |
| Host resolver silently picks another face | Resolver returns one exact path or a diagnostic; fake provider tests ambiguity and absence. |
| Draft system file reaches corpus/evidence | Keep resolution outside Context/Scene and reject it at immutable entry points; CI corpus uses only package/context assets. |
| Broad migration leaves a parallel reader | Migrate all public Theme/Layout resources atomically and delete prior live readers. |

## Conclusion

The design preserves the repository's authority chain and does not introduce
renderer-owned layout or host-dependent immutable input.  Implementation may
proceed only through an atomic migration plan that tests all text consumers and
all target adapters together.
