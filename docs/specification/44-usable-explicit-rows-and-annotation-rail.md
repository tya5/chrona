# 44. Usable explicit rows and annotation rail

## Explicit-row members

Each explicit ReviewRow member remains an independently addressable ReviewItem. When `visibility.labels` is enabled, Scene composition emits one member-label Text primitive adjacent to that member's mark, using the item's title and the `text` role. Automatic rows retain their existing table label behavior; this rule introduces no new table source or renderer contract.

Mark geometry is independent of the number of members in its row. Theme metric `timeline.mark.blockSize` supplies the common mark block size. Layout may offset stacked members vertically, but it MUST NOT shrink their mark size as member count rises. If the requested row cannot accommodate the resulting stacked tracks, Layout grows the row naturally and records visible overflow; it does not refuse a valid fit shortage.

Each mark contributes concrete start/end ports. A relation between members of the same row routes between their distinct mark ports; a coincident port is rejected as `E_PRESENTATION_ROUTE_UNAVAILABLE`, never passed as a one-point Path to a renderer.

A snapshot member uses visual role `snapshot`; Theme defines `snapshot.fill`. Primary uses `planned` and actual uses `actual`. No legacy Theme/Settings paint map is consulted.

## Annotation rail

For an object-anchored callout and an `annotations` Layout slot, Scene places the annotation box in that rail at the anchor's block coordinate, clipped only against other rail boxes and viewport bounds. Its leader starts at the mark port and routes from timeline to rail. Timeline row rectangles are not candidate-placement obstacles.

A required annotation with no fitting rail position uses a stable visible
placement and, when necessary, a direct leader route with Layout warnings.
An optional annotation may be omitted only under its explicit policy. This
is a Layout placement rule, not a new annotation resource.

## Boundary with slide vocabulary

This specification deliberately excludes overlay tracks, group headers, calendar bands/as-of markers, legend swatches, and configurable label formats. Those are additive Review vocabulary owned by #42.
