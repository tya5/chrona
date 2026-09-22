# Issue 276 Theme Metric Requirement Correction

## Trigger

The current group-header path treats `timeline.groupHeader.blockSize` as globally
optional while Theme metrics are resolved, then converts its absence into
`E_LAYOUT_GROUP_HEADER_OVERFLOW` in `compose_surface_layout`. This conflates a
missing Theme declaration with a geometric capacity failure and makes the diagnostic
depend on a late consumer.

## Corrected boundary

A Theme metric may be optional for a general Theme but required by a particular
resolved Presentation request. The render-use-case assembles that request-dependent
metric requirement from the normalized View before measurement. Theme metric
resolution receives the explicit requirement set and emits
`E_THEME_METRIC_REQUIRED` at `/body/metrics/timeline.groupHeader.blockSize` when a
header-group View requires the absent binding.

`measure_sources` carries only successfully resolved metric values into Layout.
`compose_surface_layout` consumes `timeline.groupHeader.blockSize` as an already
validated input whenever `group_presentation == "header"`; it does not select a
Theme error code or fallback size. Layout continues to own
`E_LAYOUT_GROUP_HEADER_OVERFLOW` only when a declared, positive header metric cannot
fit the resolved surface allocation.

## Consequences

The requirement derivation is View/Presentation policy, not a property inferred by
Scene or the renderer. Direct unit construction of `MeasuredSources` remains a test
fixture seam, while production rendering must validate requirements before layout.
The implementation must cover both the header-required failure and a non-header View
using the same Theme successfully, so no global requirement is accidentally added.
