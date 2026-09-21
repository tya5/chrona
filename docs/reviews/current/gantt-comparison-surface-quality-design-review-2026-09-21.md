# Gantt Comparison Surface Quality — Design Review

**Decision:** Design complete; implementation planning is authorized, subject to the foundation-completion correction.
**Scope:** Issue #58, ADR-0031, Specification 50.

## Review findings

| Review question | Finding |
| --- | --- |
| Is this a YAML-only defect? | No. YAML enables dense labels/relations and omits group/legend configuration, but the current runtime overlaps required text and accepts unreadable routes instead of applying declared overflow policy. |
| Is the solution general? | Yes. The new request/placement boundary applies to every Gantt View and Layout without project/example identifiers. |
| Is a structural refactor required first? | Yes. Layout geometry currently lives in Scene. ADR-0031 requires the move before functional behavior. |
| Does it preserve semantic boundaries? | Yes. Project facts stay immutable; View declares intent; Theme supplies values; Layout owns feasibility; Scene serializes semantics as primitives. |
| Does it add PowerPoint or hand-edit coupling? | No. SVG/PNG remains the complete generated artifact. |
| Are failure behaviors explicit? | Yes. Diagnose, ellipsize-with-source, and suppress are deterministic and provenance-preserving. |

## Cross-boundary checks

1. `SurfaceLayoutRequest` is derived only from validated PresentationContract, Layout Manifest, ThemeTokenView and declared FontMetrics.
2. `SurfacePlacement` is immutable and sufficient for Scene; no raw View/YAML lookup, FontMetrics call or router call remains in Scene.
3. New View/Layout syntax is normalized exactly once at ingress; legacy shorthand has one documented mapping.
4. Table, label, group, relation and legend verification occurs on placements before renderer output.
5. Materializer byte identity is retained and supplemented with PNG visual evidence.

## Foundation correction

The initial I58-1 delivery introduced placement records but did not remove Scene's font measurement, label positioning, or router invocation. It therefore does not meet Cross-boundary check 2. The foundation-completion correction is required before I58-3; it preserves the approved design and makes the original refactor gate objectively testable.

## Refactor order

1. Introduce request, placement and invariant modules with characterization tests over current geometry.
2. Migrate table/row/track/axis geometry out of `v05_builder` with unchanged visible behavior.
3. Migrate labels, relation routing, group headers and legend placement.
4. Enable the new schema/policies, diagnostics and neutral fixtures.
5. Update HALCYON resources and regenerate evidence through the public materializer.

## Decision constraints for implementation

- No example-specific condition, fixed pixel offset, SVG edit, or renderer fallback is permitted.
- A new layout/surface concern discovered during implementation pauses the affected slice and returns it to Specification 50 and this review.
- The implementation plan must preserve the inventory and acceptance identifiers in the completion-and-acceptance design.

With these conditions, the design has one geometry authority and closed acceptance evidence. Implementation planning may begin.
