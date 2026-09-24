# Architecture Review: Endpoint Annotation Evidence (#386)

**Decision:** Accepted.

| Boundary | Finding | Decision |
| --- | --- | --- |
| Project -> View | Project notes are durable semantic facts; endpoint callouts are audience-specific presentation intent. | Keep separate, with documented relationship. |
| View -> Layout | v0.13 admits exactly object/facet/endpoint anchors Layout resolves. | Accepted. |
| Layout -> Scene | Box placement, ports, collision avoidance, and routing are completed before Scene projection. | Accepted. |
| Scene -> adapter | Annotation box/text/leader primitives are serializable evidence, not instructions to route. | Accepted. |
| Theme -> geometry | Appearance is Theme-bound; marker geometry remains #384 work. | Accepted. |
| corpus -> materializer | New Context changes only View selection and is byte-pinned through the ordinary materializer. | Accepted. |

The review rejects a second semantic annotation model and rejects target-local
routing.  The selected Controller Z slide exercises a real declared slot with
two competing annotation boxes, which is stronger evidence than isolated
router tests while preserving the existing source-to-Scene authority flow.
