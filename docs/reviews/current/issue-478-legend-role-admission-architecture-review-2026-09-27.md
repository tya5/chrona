# Architecture Review — Legend-Only Paint Admission (#478)

**Reviewed:** [legend admission amendment](../../design/issue-478-legend-role-admission-amendment-2026-09-27.md),
the #478 rebase and axis amendments, [#427 legend dispatch](../../design/issue-427-legend-swatches-design-amendment-2026-09-26.md),
Specifications 07/33, Review Detail Profile v0.1 schema, Layout swatch
construction, Scene paint families and SVG/PNG adapters.

**Decision:** retain #427's explicit fallback as a bounded potential
consumer. It admits only portable fixed-square paint for an otherwise
unregistered name. Known Text, Icon, Path and geometry roles keep their
own stricter intersections; no role gains an unsupported property merely
because it could be mentioned in a legend. This keeps Theme load
View-independent and avoids inventing a new compatibility alias or
adapter-side policy. The remaining typo/unused-role limitation is explicit,
not misreported as issue #478 acceptance. No public output or schema changes.
