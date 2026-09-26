# Architecture Review — Connector Corridor Amendment (#466)

**Reviewed:** [corridor amendment](../../design/issue-466-connector-corridor-amendment-2026-09-26.md) against Specifications 06, 08, 33 and 44, the [topology review](issue-466-annotation-connector-topology-architecture-review-2026-09-26.md), and the controller-z public rail example.

The correction concerns only a Layout search bound. The attachment point is completed by Layout from a selected box; no View coordinate or Scene-side routing is introduced. The box still uses its full measured bounds for fit and collision, while the connector uses its source/attachment corridor. The single obstacle inventory, route quality, finite crossing policy and visible fallback remain unchanged. **Decision:** accepted as the topology design base; the generated output still requires rendered acceptance before O2 publication.
