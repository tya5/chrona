# Gantt Comparison Surface Quality — Implementation Plan

**Status:** Authorized by ADR-0031, Specification 50, the #58 design review and the atomic-rollout amendment.

## Preconditions

- Main contains the D58-1 plan, ADR-0031, Specification 50, completion/acceptance design and approved review.
- No legacy Settings/Theme or example-ID path may be reintroduced.
- Every slice must pass its focused tests before publication; failures that reveal an omitted owner return to design.
- A user-visible feasibility-policy change and every affected resource adaptation are one mergeable unit.

## I58-1 — Placement foundation refactor

Introduce immutable `SurfaceLayoutRequest`, `SurfacePlacement`, `TextPlacement` and `RelationPlacement`, plus `assert_surface_placement`. Migrate all current table/row/track/axis geometry, font measurement, label candidate selection and relation routing from Scene to Layout with characterization fixtures and no intentional SVG change. This is complete only when Scene consumes completed placements and does not import or invoke font metrics or routing.

The executable decomposition and measured baseline are recorded in `gantt-comparison-surface-layout-foundation-implementation-plan-2026-09-21.md`.

**Evidence:** Scene no longer imports FontMetrics or routing; placement identity and current materializer bytes remain stable.

## I58-2 — Atomic table feasibility

Replace uniform shrink placement with per-column measured minima, deterministic allocation and declared overflow behavior. In the same slice, add neutral table overflow/ellipsize fixtures, `E_LAYOUT_TABLE_OVERFLOW`, and every affected HALCYON table declaration plus regenerated public materializer evidence.

**Evidence:** A58-02, all affected contexts remain materializable, full test suite.

## I58-3 — Atomic labels and relation quality

After I58-1 is structurally complete, enable label candidate selection and relation routing-quality scoring through the completed Layout boundary. In the same slice, add normalized View/Layout policy forms, diagnostics, neutral fixtures, and HALCYON label/relation declarations plus regenerated evidence.

**Evidence:** A58-03, A58-04 and A58-06; Scene only projects accepted placements.

## I58-4 — Atomic group header and legend

Move group-header allocation and legend placement into Layout. In the same slice, add semantic registry coverage, neutral fixtures, and only the selected HALCYON resource declarations plus regenerated evidence.

**Evidence:** A58-05 and A58-08.

## I58-5 — Visual release gate

Run full pytest, conformance, all materializer checks, and declared PNG evidence review. Request external verification only after explicit user direction; do not close #58 until that gate is green.

**Evidence:** A58-07 through A58-09 and independent result.

## Publication order

Each slice is a separate PR and merge. I58-2 through I58-5 may not begin before the prior slice is merged and its design invariants are green. An incomplete I58-1 may not be treated as a completed dependency merely because its placement data types exist. No stricter behavior may make a declared main-branch context temporarily unmaterializable; resource adaptation belongs to that same slice.

## Rollback / migration

All new contracts are internal until schema normalization is added in I58-3. Existing YAML shorthand remains ingress-compatible. Generated SVG changes occur only in the atomic behavior/resource slices and are reproduced from declared contexts.
