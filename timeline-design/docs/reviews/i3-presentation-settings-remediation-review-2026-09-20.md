# I3 Presentation Settings Remediation Review

**Conclusion:** Accepted. Every presentation behavior authorized for I3 is owned by
resolved settings, retained in the completed Scene where required, and serialized
without a renderer fallback.

## Evidence

- Axis intervals retain their natural calendar bucket. Scene construction applies all
  six month formats, all three quarter formats, localized/ISO day formats, and the new
  four-digit `year` level with its dedicated typography role.
- Point shape is retained on Scene Symbols and serializes as diamond, circle, or square
  from the same bounds used by port geometry and legend layout.
- Dependency and explanatory paths retain triangle, chevron, or none. `none` emits
  neither a marker definition nor `marker-end`; marker orientation and dimensions remain
  Theme-owned.
- Planned, Actual, and Baseline marks retain the resolved facet color and opacity.
  Group overrides therefore reach both Scene and SVG instead of falling back to global
  adapter colors.
- Planned and Actual bar heights have an explicit regression proving they remain
  independently observable.
- The built-in fixture, preset schema, full settings schema, six example settings, and
  fixed-value inventory agree on the expanded settings contract.
- The verification harness no longer performs host font discovery. Its only font input
  is the already validated, content-addressed metrics-table declaration.
- All five ASTER SVG, PNG, and embedded slide artifacts were regenerated. Visual review
  confirms the title, subtitle, axis labels, table, marks, routes, legend, and coverage
  remain visible without clipping or overlap.

The focused presentation suite passes 63 tests. The full suite passes 207 tests, and
the complete Chrona conformance runner passes every stage. The only warnings are the
existing `jsonschema.RefResolver` deprecations.
