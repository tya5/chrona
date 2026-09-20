# ADR-0019: Limit the scope to what the shared presentation foundation can support

**Status:** Accepted (2026-09-20). The detailed contract is fixed by Specification 30; runtime implementation has not started.

## Context

ASTER image-generation concepts A through D are material for evaluating presentation,
not specifications for individual implementations. The project prioritizes the freedom
of the shared foundation and does not adopt expressions that need special-case support.
In particular, callouts are supported only when they can be generalized.

Existing Specifications 06 §9 and 08 §6.3 define a contract for placing annotations
from stable references and logical placement preferences. The current Gantt renderer,
however, generates SVG directly for its own use and does not sufficiently consume that
contract. This decision adds neither a new general-purpose canvas nor a separate
annotation model.

## Decision

1. Rendering MUST NOT branch on A/B/C/D, ASTER, Controller Z, or preset names.
2. Tables, axes, marks, measured text, references, connectors, and placement regions
   are shared. The placement mechanism is generalized; dependency and annotation
   semantics are not merged.
3. A callout is conditionally adopted as a text region attached to a reference and
   sourced from an existing Annotation. Its box and leader are optional decoration.
4. The initial scope is limited to rectangular text regions, decoration from an
   existing Theme, orthogonal leaders, a finite candidate set, and explicit diagnostics
   when placement fails.
5. Arbitrary-shape callouts, manual bends, arbitrary coordinates, custom scripts,
   image-matched exceptions, and unbounded automatic placement are not adopted. The
   presentation requirement is reduced when necessary.
6. A completed Scene, including shapes, text, and routes, is passed to the output
   adapter. The adapter MUST NOT lay it out again.

## Admission gate

A capability is eligible for implementation only when it satisfies all of the
following conditions:

- The same mechanism is usable by at least two distinct use cases.
- It fits an existing owner's responsibility and creates no second source of truth for
  facts or settings.
- It can be deterministically regenerated from the same closed input set without
  altering semantic values.
- Handling for unsupported input, missing references, collisions, and capacity
  exhaustion can be specified.
- It handles changed sample IDs, another project, and changed wording or viewport
  without exceptions.
- Every added setting has a type, meaning, consumer, and negative fixture.

Potential usefulness for an unspecified future use is not, by itself, an admission
reason.

## Consequences

Label placement is designed first, then the same measurement, placement, and connector
mechanism is applied to annotations and milestone explanations. No B-only milestone
panel is created. C is also evaluated as an implementation of the existing within-View
grouping and lane-stacking policy rather than as another renderer.

This ADR decides direction; it does not declare schema closure or implementation
completion. See [Specification 30](../specification/30-shared-presentation-foundation.md)
for details and the [implementation plan](../archive/planning/shared-presentation-foundation-plan.md)
for sequencing.
