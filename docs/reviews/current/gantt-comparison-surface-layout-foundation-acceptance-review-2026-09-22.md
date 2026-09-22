# Gantt Comparison Surface Layout Foundation — Acceptance Review

**Decision:** Accepted for I58-1 publication.
**Scope:** F58-1 through F58-4 of the Foundation completion plan for Issue #58.

## Boundary review

`SurfaceLayoutRequest` is composed into a complete `SurfacePlacement` in Layout.
The closure now includes measured auxiliary text, relation paths, annotation boxes,
annotation leader paths, and legend swatches in addition to the previously migrated
slots, rows, groups, scale, marks, table, axis, time decorations, and plot labels.

`v05_builder` projects those completed values into Scene primitives. It does not
import or invoke Layout text measurement, dependency routing, annotation routing, or
annotation placement helpers. Semantic purpose, role, and renderer shape selection
remain Scene responsibilities; all bounds, baselines, ports, and paths remain Layout
responsibilities.

## Characterization

The refactor preserves the published behavior. The structural test rejects direct
measurement and routing imports/calls from Scene. All declared materializer outputs
reproduce byte-for-byte without regenerating committed SVG evidence.

## Verification

- Focused Scene/Layout/resource tests: 84 passed.
- Full test suite: 247 passed (7 pre-existing deprecation warnings).
- Public materializer byte checks: ASTER `overview`, Controller Z `executive`, and
  HALCYON `mission-brief`, `programme-board`, and `launch-campaign` all passed.
- Generated SVG diff: no committed generated SVG changed.

## Follow-on ordering

This review completes only I58-1. I58-2 remains an unstarted atomic feasibility
slice until this Foundation PR is merged. No label/relation quality policy, schema
syntax, HALCYON declaration, or generated evidence change is included here.
