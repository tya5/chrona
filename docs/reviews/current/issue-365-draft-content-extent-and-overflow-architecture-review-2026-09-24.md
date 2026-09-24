# Issue 365 architecture review

## Reviewed boundaries

| Boundary | Decision | Result |
| --- | --- | --- |
| View | Remove inert `layoutIntent.compactness`. | View expresses only consumed semantic intent. |
| Draft ingress | Parse a typed fixed-or-auto request. | Convenience does not leak into evidence contracts. |
| Context | Retain a finite, immutable viewport. | Snapshot identity and materializer reproducibility remain intact. |
| Layout | Measure sources, resolve Draft block extent, place content, and own numeric overflow facts. | Geometry and fit policy have one owner. |
| Scene | Project completed finite placements. | Scene does not choose a canvas or diagnose fit. |
| Renderer | Render the supplied finite viewport. | Adapters cannot diverge in canvas policy. |

## Findings

`RenderEnvironment` currently holds two integers, and `render_review` passes
them unchanged through Layout, Scene, and renderer.  Layout source
measurements already hold row count and row minimum metrics, while the surface
composer knows the allocated timeline rectangle.  The missing connection is a
Layout-owned Draft extent resolver, not a renderer feature or a Context schema
extension.

The current View schema admits `compact`, `balanced`, and `expanded`, but the
typed View input preserves the mapping without consuming it.  Retaining it
would make a non-policy look like a policy.  Removing it is the clean boundary
correction; compatibility aliases are intentionally not retained.

The review found no reason to alter placement identity, font measurement,
relation routing, materializer byte semantics, or immutable Context validation.
