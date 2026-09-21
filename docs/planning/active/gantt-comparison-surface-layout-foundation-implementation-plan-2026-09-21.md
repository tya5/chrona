# Gantt Comparison Surface Layout Foundation — Completion Implementation Plan

**Status:** Authorized by ADR-0031, Specification 50, the #58 design review, and the foundation-completion correction.
**Scope:** Complete I58-1 before enabling I58-3 behavior.

## Measured baseline

At commit `67b6980`, the focused Scene/Layout suite passes 17 tests, the full suite passes 239 tests, and all five declared example slides reproduce through the public materializer. `v05_builder` still directly performs five font measurements, one dependency-route invocation, and one annotation-leader route invocation. The completion work must preserve those bytes and diagnostics before it enables new policy behavior.

## Ownership boundary

`SurfaceLayoutRequest` receives the normalized presentation contract, resolved slots, measured sources, theme typography, font metrics, review rows/items, and capabilities. `SurfacePlacement` returns immutable geometry records for:

- slots, rows, groups, temporal scale, mark bounds, and ports;
- every measured text layout, including title, table, group, axis, as-of, legend, notes, summary, labels, and annotations;
- dependency and annotation-leader paths; and
- optional/suppressed placement records and ordered diagnostics.

Scene maps completed records to `SceneSlot`, `SceneRow`, `SceneGroup`, `SurfaceScaleManifest`, and `ScenePrimitive`. It may select semantic roles and shapes from the normalized contract/theme, but may not calculate a bound, text width, text baseline, label coordinate, port, or path.

## Execution slices

### F58-1 — Typed placement closure

Extend the internal placement model with renderer-neutral primitive geometry records and a text-layout record that carries measured bounds, baseline, lines, typography, and font asset identity. Add invariants for required text bounds, marks/ports, and completed/suppressed routes. Add neutral characterization fixtures that assert canonical placement identity without changing Scene output.

### F58-2 — Layout composition extraction

Implement one Layout composition function that derives the complete placement closure from `SurfaceLayoutRequest`. Move slot/row/group/scale, table allocation, text measurement, axis fitting, mark and port geometry, plot-label candidate coordinates, dependency routes, annotation boxes, and annotation leaders into it. Keep the existing policies and their current defaults unchanged; F58-2 must not add the I58-3 schema syntax or quality/suppression policy.

### F58-3 — Scene projection reduction

Make `build_scene_input` obtain the completed placement closure before Scene construction. Reduce `compose_review_surface` to mapping accepted placements to Scene model records and attaching semantic IDs/roles/shapes. Remove direct font-metric and router imports/calls from `v05_builder`; no geometry helper remains there.

### F58-4 — Characterization and publication gate

Add structural tests that reject font-metric/routing use in Scene, placement-to-Scene projection tests, and byte characterization for the declared materializer contexts. Run focused tests, full pytest, all public materializer checks, and a diff check proving no generated SVG change. Publish the completed foundation slice as one PR, then start I58-3.

## Non-goals and controls

- Do not add `labels.overflow`, relation object syntax, route-quality limits, or HALCYON policy declarations in this foundation slice; those belong atomically to I58-3.
- Do not add example-specific coordinates, SVG edits, or renderer fallbacks.
- If extracting an existing geometry calculation exposes an omitted source or policy owner, return to the #58 design documents before changing behavior.

## Acceptance

F58-4 is accepted only when `v05_builder` contains no `font_metrics`, `route_orthogonal`, or annotation-route invocation; focused and full tests pass; all five example slides materialize byte-identically; and the diff contains no generated SVG changes.
