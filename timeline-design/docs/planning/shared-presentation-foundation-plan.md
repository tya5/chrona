# Shared Presentation Foundation Design and Implementation Plan

**Status:** G0 design completed and published on 2026-09-20. No runtime change.
**Basis:** ADR-0019 and Specification 30. A through D are acceptance images; they do
not require individual renderers.

## Priority and gates

| Stage | Scope | Exit condition |
|---|---|---|
| G0: overall design closure | G1–G4 owners, internal IR, wire schemas, migration, shared measurement/placement, diagnostics, and fixtures | Every checklist item below is closed. Publish design before G1. |
| G1: correct existing contracts | Settings consumption, text measurement, preservation of Actual/variance semantics, common Scene path | Verify consumption under settings variation. Unknown/unsupported values diagnose explicitly. Update mapping to unfinished P1–P5 work. |
| G2: shared A/D presentation | Month/week axes, nearby labels, planned/actual presentation, group×facet color | Use the same mechanism for ASTER and another project; test arbitrary IDs, long text, Japanese text, and viewport variation. |
| G3: annotations and explanation bands | Notes and point explanations through shared anchors, text regions, and leaders | Exercise at least two use cases with the same implementation. Exclude expressions that cannot be generalized; do not make them work by exception. |
| G4: lane placement | Stable stacking coordinated with labels and connectors | Admit only scope that works with the G2/G3 measurement, obstacle, and routing mechanisms. |

G0 also fixes the G3/G4 boundary so the foundational model need not be rebuilt later.
Diagrams that cannot be supported by a finite method remain out of scope and are
recorded in specification, diagnostics, and fixtures. Do not extend a search engine or
DSL without bound merely for difficult presentation.

## G0 checklist

- [x] Confirm generalization from existing Specifications 06/08 annotations and Scene primitives.
- [x] Limit initial annotations to selected objects, rectangular text, and optional leaders.
- [x] Exclude sample/preset branches, arbitrary coordinates, free-form shapes, and manual bends.
- [x] Record a single owner, no implicit fallback, and separation of source from dependency.
- [x] Complete owner, type, default-preset, and consumer mapping for every new/existing field.
- [x] Complete normalized schemas for shared scales, projection instances, facets, and endpoints.
- [x] Fix display rules for font measurement, locale, week boundaries, and half-open intervals.
- [x] Fix candidate generation, search order, search limits, and diagnostics for every layout policy.
- [x] Define migration from legacy View/Scene/Layout plus rejection of duplicate declaration.
- [x] Resolve conflicts between Specification 28 milestones/View selection and Specification 29 legacy scope.
- [x] Provide positive/negative fixtures and validators and complete the cross-design consistency review.

G0 design completion does not mean implementation completion, P1–P5 completion, or
migration of every output path. Before G1, review the implementation scope against
this contract.

## Shared acceptance matrix

| Perspective | Required cases |
|---|---|
| Uses | Bar name, finish date, work note, planned-gate explanation, table cell |
| Fact preservation | Planned/Actual/variance/dependency-edge sets remain invariant under decoration or placement changes |
| References | Unknown ID, hidden target, missing Actual, span/point endpoint mismatch, multiple projections of one target |
| Annotations | Distinguish semantic from presentation; a leader does not become a dependency |
| Geometry | Long text, bold text, Japanese text, box overflow, text obstacles, unroutable paths, very narrow viewport |
| Reproducibility | Same closed input produces the same Scene/output across processes; input assets are fixed by version/hash |
| Generality | Replace every object ID and change team count, dates, and wording; no special branch in another project |
| Schema | Detect unused settings, unknown values, duplicate ownership, and illegal facet/role mapping |
| Boundary | Reject decoration requiring a dedicated implementation; do not promise to solve every feasible diagram |

Do not accept on image comparison alone. Report structure, semantics, geometry, and
images separately. Do not reuse the existing 127 passing tests as evidence of a new
capability or design completion.

## Publication and protection of existing work

At the end of the design stage and each implementation stage, review only the target
diff and publish it non-force. Do not include uncommitted work or work published
previously. When design changes are required, pause related implementation and first
synchronize the affected specification, schema, fixture, plan, and acceptance criteria.
Do not exception the contract merely for image fidelity.
