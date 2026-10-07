# 44. Usable explicit rows and annotation rail

## Explicit-row members

Each explicit ReviewRow member remains an independently addressable ReviewItem. When `visibility.labels` is enabled, Scene composition emits one member-label Text primitive adjacent to that member's mark, using the item's title and the `text` role. Automatic rows retain their existing table label behavior; this rule introduces no new table source or renderer contract.

Mark geometry is independent of the number of members in its row. Theme metric `timeline.mark.blockSize` supplies the common mark block size. Layout may offset stacked members vertically, but it MUST NOT shrink their mark size as member count rises. If the requested row cannot accommodate the resulting stacked tracks, Layout grows the row naturally and records visible overflow; it does not refuse a valid fit shortage.

Each mark contributes concrete start/end ports. A relation between members of the same row routes between their distinct mark ports; a coincident port is rejected as `E_PRESENTATION_ROUTE_UNAVAILABLE`, never passed as a one-point Path to a renderer.

A snapshot member uses visual role `snapshot`; Theme defines `snapshot.fill`. Primary uses `planned` and actual uses `actual`. No legacy Theme/Settings paint map is consulted.

## Annotation rail

The rail is one configuration of the [unified annotation candidate model](06-view-model.md#9-annotations-and-layout-intent): an `annotations` slot region, row-aligned search, shared completed-surface obstacle query and leader connector from the mark port. Timeline row rectangles are not candidate-placement obstacles. Layout completes the box and leader; Scene projects them unchanged. Legacy rail declarations normalize to this candidate without changing their output.

A required annotation with no fitting rail position uses a stable visible
placement and, when necessary, a direct leader route with Layout warnings.
An optional annotation may be omitted only under its explicit policy. This
is a Layout placement rule, not a new annotation resource.

After ordinary rail search exhausts, visible-overflow completion may retain
the full natural frame's inline overhang while searching the same finite
vertical positions against the shared obstacle inventory. If no position
fits, place the frame below all preceding completed rail boxes and list
records, including unnumbered boxes. Track full box extents, not only body
text. The box and required heading/body text carry the visible-overflow
disposition and existing warnings. Ordinary fitting candidates and numbered
list order remain unchanged; required peer notes must not share a clamped
fallback position.

## Boundary with slide vocabulary

This specification deliberately excludes overlay tracks, group headers, calendar bands/as-of markers, legend swatches, and configurable label formats. Those are additive Review vocabulary owned by #42.
