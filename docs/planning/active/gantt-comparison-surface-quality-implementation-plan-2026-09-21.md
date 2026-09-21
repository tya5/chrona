# Gantt Comparison Surface Quality — Implementation Plan

**Status:** Authorized by ADR-0031, Specification 50 and the #58 design review.

## Preconditions

- Main contains the D58-1 plan, ADR-0031, Specification 50, completion/acceptance design and approved review.
- No legacy Settings/Theme or example-ID path may be reintroduced.
- Every slice must pass its focused tests before publication; failures that reveal an omitted owner return to design.

## I58-1 — Placement foundation refactor

Introduce immutable `SurfaceLayoutRequest`, `SurfacePlacement`, `TextPlacement` and `RelationPlacement`, plus `assert_surface_placement`. Migrate current table/row/track/axis calculations from Scene to Layout with characterization fixtures and no intentional SVG change.

**Evidence:** Scene no longer imports FontMetrics or routing; placement identity and current materializer bytes remain stable.

## I58-2 — Table feasibility

Replace uniform shrink placement with per-column measured minima, deterministic allocation and declared overflow behavior. Add table overflow/ellipsize fixtures and `E_LAYOUT_TABLE_OVERFLOW`.

**Evidence:** A58-02, schema/conformance updates if required, full test suite.

## I58-3 — Labels, groups, legend and relations

Move label candidate selection, relation routing-quality scoring, group-header allocation and legend placement into Layout. Add normalized View/Layout policy forms, diagnostics, semantic registry coverage and neutral fixtures.

**Evidence:** A58-03 through A58-06; Scene only projects accepted placements.

## I58-4 — Resource adaptation and generated evidence

Update HALCYON resources only through approved public YAML forms: explicit label/relation overflow; group-header metric/presentation where selected; legend slots where reader need warrants it. Materialize all declared slides only through the public tool.

**Evidence:** A58-08, generated SVG diffs, no hand edits.

## I58-5 — Visual release gate

Run full pytest, conformance, all materializer checks, and declared PNG evidence review. Create a separate external-verification issue carrying the target main SHA and commands; do not close #58 until that gate is green.

**Evidence:** A58-07 through A58-09 and independent result.

## Publication order

Each slice is a separate PR and merge. I58-2 through I58-5 may not begin before the prior slice is merged and its design invariants are green. YAML changes are prohibited before I58-3 is merged.

## Rollback / migration

All new contracts are internal until schema normalization is added in I58-3. Existing YAML shorthand remains ingress-compatible. Generated SVG changes are expected only in I58-4 and are reproduced from declared contexts.
