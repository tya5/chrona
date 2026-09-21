# M27 Completed-Scene Migration Design Amendment — 2026-09-21

**Status:** Reopens D27-2 through D27-5; M27 implementation is paused.

## Discovery

The pre-M24 completed Scene builder and `scene_svg` serializer are not directly
consumable by the current product resources. They depend on removed presentation
settings schemas and a legacy resolved Theme shape (`paints`, `strokes`, typography,
marker and pattern maps). Current Render Context v0.5 resolves Theme v0.2 values and a
Layout Profile v0.2 Manifest instead. Reconnecting the old modules would violate the
M24 replacement boundary and introduce an undocumented second configuration model.

## Corrected decision

M27 retains ADR-0028's single public completed-Scene route, but it MUST implement a
new generic **v0.5 Scene builder and SVG token adapter** over only these current inputs:

`ResolvedPresentationInput + resolved Layout Manifest + Theme v0.2 resolved values +
Color Scheme resolved colors + explicit font metrics`.

The old builder and serializer are reference-only behavior inventories. They may not be
revived, imported, or adapted through a legacy settings compatibility layer.

## Required closure work

1. Define a versioned internal resolved Theme token view: a derived, non-persistent
   mapping from Theme v0.2 roles/values to the closed Scene needs (typography, paint,
   stroke, marker, pattern, opacity, geometry tokens). It has no renderer defaults.
2. Define the v0.5 Scene builder's input/output type contract, including how Layout
   Manifest slots map to Scene slots/rows/groups and how the existing axis, marks,
   labels, routing, annotations, and normalized surface content mechanisms participate.
3. Replace the legacy serializer's direct settings reads with only completed primitive
   properties and the derived resolved token view; identify a stable diagnostic for
   every missing token.
4. Update the D27 inventory, policy binding, acceptance design, and final review with
   this migration boundary; only then prepare a corrected implementation plan.

## Non-negotiable invariants

- No legacy schema/parser, old settings document, compatibility fallback, or source-ID
  branch is added.
- Theme v0.2/Color Scheme remain declarative user inputs; the derived token view is
  rebuilt per immutable Context and never persisted.
- Layout Profile v0.2 remains the only geometry-authoring input.
- Project/Schedule/Actual semantics and target capabilities remain unchanged.
