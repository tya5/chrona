# Issue #1279 — architecture review

[Selected contract](../../design/issue-1279-canvas-viewport-design-2026-10-10.md).
Decision: accepted for implementation planning; release evidence is not yet met.

| Authority / adjacent contract | Consistency finding |
| --- | --- |
| Spec 33 §§1, 13–13.1 | Context owns declaration; Layout owns completed extent. Preserve original dimensions before allocation grows, not a renderer-side warning. |
| Spec 50 placement closure | Warning consumes completed native slot/geometry identities; no new selection, measurement, route, or collision policy. |
| Spec 08 §§5, 8 | Scene carries completed metadata and stable warning identity; adapters still serialize unchanged geometry. |
| Spec 66 §3 / #918 | One typed report producer supplies human-readable CLI/MCP warnings, including details; stderr parsing is not introduced. |
| Draft auto block / #1299 | Null block declaration prevents a false height constraint. Negative inline origin is still checked. |
| #1291 / #1292 | Diagnose existing overflow without silently fixing marks or labels in this slice. |

Review risks: both surfaces must receive the original declaration; attribution
must include content-adjusted slots and exclude self-derived canvas treatments.
Verify every current artifact's actual SVG extent and shared warning membership.
