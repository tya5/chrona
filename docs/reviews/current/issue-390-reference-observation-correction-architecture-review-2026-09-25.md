# Architecture Review: Source observations in the presentation matrix (#390)

**Decision:** Approve the correction.

| Boundary | Review | Result |
| --- | --- | --- |
| Capability identity | #391 remains the only owner of capabilities and Chrona disposition. | Pass |
| Research facts | A finite tool-local table records source observations without runtime authority. | Pass |
| Honesty | `unknown` is a required explicit value, not an absent cell or inferred negative. | Pass |
| Product scope | External products are compared only at the named finite category; no equivalence or adoption commitment is implied. | Pass |
| Extensibility | Adding a source requires adding one observation to every existing closed capability row, so coverage cannot silently become uneven. | Pass |

The correction preserves the Scene/Layout/Theme/adapter responsibility split:
the matrix observes capabilities after the fact and does not authorize one.
