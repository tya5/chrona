# M27 I27-R6 Rich Primitive Implementation Review — 2026-09-21

**Decision:** Complete and published.

R6 implements only the current-resource design: Theme v0.2 role bindings now declare
font size and line height, and `TextLayout` carries the completed typography to SVG.
Object annotations resolve their existing facet/endpoint references against projection
marks, use their `annotations` Layout Manifest slot for measured placement, and retain
bounded leader provenance. Routed dependencies carry a declared marker token; SVG
emits only referenced marker definitions and endpoint attachments.

Evidence: 200 regression tests pass; full conformance passes; and both example
materializers reproduce their expected SVG through the public CLI. The implementation
does not import Settings, legacy paint maps, raw authoring resources in the SVG
adapter, example-specific branches, or authored coordinates.
