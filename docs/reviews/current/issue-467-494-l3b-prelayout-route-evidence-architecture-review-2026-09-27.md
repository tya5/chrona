# Architecture Review — L3b Lane Preflight and Route Evidence (#467, #494)

**Decision:** accept the [L3b design correction](../../design/issue-467-494-l3b-prelayout-route-evidence-correction-2026-09-27.md) for implementation planning; do not accept lane-mode product output or either issue. **Plan:** [design plan](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-design-plan-2026-09-27.md). **Public base:** L3a allocator `1cc86e1f` and its [CI-backed review](issue-467-494-l3a-neutral-allocator-implementation-review-2026-09-27.md). This review is about the contract; CI for a later implementation is not evidence here.

## Whole-architecture checks

| Authority or adjacent design | Consistency finding |
| --- | --- |
| Specifications 06/08, 38 §3.1 and 50 §§2–3 | Project/Schedule retain dates and dependency meaning; View retains selection/grouping/label intent; Theme/FontMetrics provide measured assets; Layout alone closes inline footprint, lane membership, height, labels and route outcomes. Scene remains completed-primitive/diagnostic projection; SVG/PNG remain serializers. The living 38/50 contracts now state the preflight and route evidence rather than leaving them only in a design note. |
| Specification 24 and #487 measured table columns | A conservative finite `Lane`/`Items` candidate text envelope enters the existing measured-column path before allocation. Exact cells are derived from the immutable lane plan and must fit the envelope. This is not a parallel View/Scene table-width heuristic. |
| #468 content-coherent host solve and #480 table-text row extents | The same lane plan provides natural row requirements to the existing content-height resolver and final composer; table text line block remains an input. This removes the late-height cycle. A seed manifest supplies inline slots only; final block positions remain the normal solve's authority. |
| #481 group header/band and #486 attached milestones | Expanded lane rows and header are included in one group extent. An attached point keeps its source identity, uses its host lane, and is part of the measured collision footprint. Neither group paint nor attachment is an implicit new row allocator. |
| #466 route-priority correction and #494 no-crossing gate | Required packed names/deltas precede routes and remain obstacles. Route-anchored relation labels necessarily follow their completed paths. Host-mark egress exemptions do not apply to required text. Attempt causes are typed in Layout, not inferred by Scene or a post-hoc SVG scan. |
| #467 selected design, L0 feasibility and current 4wd HALCYON Project | The existing canonical identity, 3-row ladder, first-fit/predecessor preference, 4wd current-plan chain, ≤12 acceptance and no packed-name suppression remain. Old WIP counts do not become release evidence. |
| #498 Editorial/default acceptance | This correction does not select a default or alter any catalogue entry. The separately published Editorial/default decision and its architecture review are still required before L3c, even if L3b's hidden path passes. |

## Alternatives and failure boundaries

Late allocation would make the content-height measurement false; independent allocations would permit table/row/mark drift; a generic `ValueError` catch would disguise programming defects as route search exhaustion; endpoint label exemptions would violate #494. These are rejected. The selected one-preflight/one-realization contract is finite and testable. A Layout Profile with block-dependent inline size is diagnosed `E_LAYOUT_LANE_INLINE_UNSTABLE`; it is not assigned guessed coordinates. If a public profile actually requires such coupling, implementation must stop and return to design for a declared iterative solve. If a mark/summary footprint proves unavailable before preflight, implementation must likewise return to design rather than add a late patch.

No new View schema or Scene schema is selected here. The route cause travels as a typed Layout result and a stable lane-specific diagnostic; automatic/explicit public bytes remain a characterization gate. This keeps the correction scoped to ownership and measured evidence, while preserving intentional View v0.27 incompatibilities and immutable Context semantics. The final implementation plan must name the exact interfaces, fixtures and generated-output checks and publish separately before code changes.

## Review result

The corrected contract closes the identified cross-layer cycle and route-cause ambiguity without weakening route quality or required-label visibility. It is approved for L3b implementation planning only. L3b must prove the final inline invariant, all footprint classes, one-to-one table/lane identity, typed attempt invariants, 02/11/12 label-route non-crossing, unchanged automatic bytes and current-main HALCYON counts. Failure of any acceptance measure reopens design before public activation.
