# Architecture Review — View v0.27 Lane Contract (#467)

**Reviews:** [v0.27 contract clarification](../../design/issue-467-view-v027-contract-clarification-2026-09-27.md). **Amends:** the [phase/version review](issue-467-lane-rows-phase-correction-architecture-review-2026-09-27.md). **Plan:** [L2 implementation amendment](../../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md).

## Decision

The clarification is consistent with the selected lane design and Specification 38. It closes the v0.27 schema boundary without adding lane geometry or changing existing `automatic`/`explicit` behavior. L2 remains a dormant, fail-closed contract slice; lane rendering and its acceptance evidence remain L3 responsibilities.

| Boundary | Contract checked | Result |
|---|---|---|
| View grammar | Specification 38 §3.1 and selected #467 design | `laneTable` is lane-only; `tableColumns` remain item-subject declarations and are excluded from generated lanes. Lane summary does not invent a table subject. |
| Delta migration | #467 literal acceptance row 4 and selected design | `finishDelta` is required when a migration removes an existing visible delta promise. The source View supplies that fact, so the schema does not require deltas in every lane View. L3 must verify every migrated View and its rendered output. |
| Layout and routing | #466 route-priority correction; Specifications 24, 38, 50; #480/#481/#487 | No ownership or phase change: Layout measures the lane table and required labels, sizes rows, registers labels in the shared obstacle index, then routes dependencies. |
| Context and resources | Specifications 15/40/50; Render Context v0.16 | View references keep their current IDs, addresses and revision tokens. The schema inventory and packaged schema source remain the resource authorities. |
| Adjacent designs | #486 attached milestones; #488 containment; #498 bundled default | Attachment, containment and default-readability work remain owned by their existing slices. This amendment changes no preset selection and no bundled output. |

## Verification and limits

Focused L2 evidence covers lane grammar acceptance, rejection of `laneTable` in `automatic`/`explicit`, typed normalization and the unsupported-mode diagnostic. It does not establish lane placement, delta visibility in rendered output, route behavior, or public artifact freshness. The L2 publication must rebase on the accepted L1 base and regenerate/check the full public materializer batch; Scene provenance changes with the View content identity, while SVG output is expected to remain byte-identical for L2-only changes.

**Disposition:** proceed with the scoped schema correction and focused tests. No additional normative change is selected beyond the clarification recorded in Specification 38 §3.1.
