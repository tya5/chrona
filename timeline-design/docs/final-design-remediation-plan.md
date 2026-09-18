# Final Design Remediation Plan

**Status:** Draft  
**Version:** 0.1  
**Purpose:** Close every finding from the 2026-09-17 cross-document final design review before declaring Chrona ready for minimal implementation.  
**Authority:** The owning specifications remain normative. This document owns only the remediation order, evidence, and completion gate.

## 1. Decision and scope

The final design review found that the design-completion gate in
`design-documentation-plan.md` is **not met**. In particular, several documented
contracts cannot yet be implemented or independently verified without inventing
semantics. Therefore this plan temporarily supersedes any earlier claim that the
Presentation or end-to-end design is complete.

This is a design and conformance program. It does **not** authorize a GUI, renderer,
CLI, AI adapter, or other minimal-product implementation. Existing Core v0.1 code and
fixtures remain useful evidence, but no maturity claim is inferred from their presence.

The plan preserves the product boundary: Git-friendly structured temporal data is
canonical; presentation is expressive but derived; Chrona is not a general-purpose PM
suite; and a local GUI edit must not require unrelated scene/UI replacement.

## 2. Remediation rules

1. Close semantics in their authoritative owner before changing dependent schemas,
   fixtures, runners, or implementation.
2. A schema may reject structural invalidity, but semantic validation MUST diagnose
   constraints that require resolving a resource graph or evaluating a projection.
3. Every finding receives a positive fixture and at least one negative fixture with
   expected diagnostic identifiers. A passing positive fixture alone is insufficient.
4. A document status may advance only after its own listed evidence is complete;
   unverified cross-document claims are corrected rather than carried forward.
5. An implementation may consume only contracts that have passed the relevant focused
   review. This prevents the rework risk of letting a prototype choose semantics.

## 3. Finding inventory

| ID | Severity | Finding | Primary owner | Dependency |
|---|---|---|---|---|
| R1 | High | Plan/Actual comparison lacks closed delta, point-observation, baseline, and multi-observation rules. | `06-view-model.md`, `13-presentation-format.md` | R3 |
| R2 | High | SceneDelta prose, schema, and validation disagree; local impact cannot be proved. | `08-scene-and-rendering.md`, `runtime-reactivity-design.md` | R3, R8 |
| R3 | High | Resource references do not resolve an immutable, reproducible revision closure. | `13-presentation-format.md`, `09-application-architecture.md` | — |
| R4 | High | Runtime evaluation content identity is conflated with request ordering and stale-result handling. | `runtime-reactivity-design.md` | R3 |
| R5 | High | Style/Theme cannot deterministically resolve roles to concrete visual values. | `07-style-and-theme.md` | R6 |
| R6 | High | View, annotation, and layout semantics are incomplete or internally inconsistent. | `06-view-model.md` | R1 |
| R7 | High | Command registry, payload, batch, result, and external-identity contracts are incomplete. | `10-command-model.md`, `13-presentation-format.md` | R1, R3 |
| R8 | High | Extension package manifest, references, inheritance, and validation are incomplete. | `11-extension-model.md`, `05-project-format.md` | R3 |
| R9 | Medium | Readiness/status documents make stale or premature claims. | review/readiness documents | R1–R8 |
| R10 | Medium | Conformance is mostly happy-path shape validation and CI does not run the full test suite. | `12-quality-and-invariants.md`, conformance artifacts | R1–R8 |

## 4. Ordered work program

### Phase 0 — Establish a truthful review baseline

**Status:** Completed — 2026-09-18

**Addresses:** R9

Update `design-completion-readiness-review.md`,
`use-case-design-readiness-review.md`, and affected status labels so they explicitly
refer to this open remediation program. Reconcile `13-presentation-format.md` and
`14-use-case-catalog.md` status with their unresolved blocking contracts; they MUST NOT
be described as implementation-ready.

**Done when:** every readiness claim names its evidence and none says the final gate is
satisfied while R1–R8 remains open.

### Phase 1 — Define revision-bound evaluation closure

**Status:** Completed — 2026-09-18

**Addresses:** R3; prerequisite for R1, R2, R4, R7, and R8

Define a common resource-reference grammar and normalization algorithm in
`13-presentation-format.md`: resource kind and ID, canonical repository-relative path,
immutable revision/tree identity, content identity, and same-logical-project rule.
Define the evaluation manifest/closure: exact Project, Snapshot, Actual, View, Style,
Theme, Scene Profile, and extension-package contents consumed by one evaluation.

`09-application-architecture.md` defines how the loader resolves that closure and
reports missing, mismatched-kind/ID, out-of-root, cyclic, and revision-unavailable
references. The runner MUST evaluate the declared revision-bound closure, not silently
read the current filesystem.

**Evidence:** reference schemas; normal and negative closure fixtures; diagnostics for
wrong ID/kind, path escape, missing revision/content, mixed logical Project, and cycle.

**Done when:** two evaluations with the same declared closure are reproducible and any
input substituted from a different revision is detectable.

### Phase 2 — Close comparison and presentation selection semantics

**Status:** Completed — 2026-09-18

**Addresses:** R1 and R6; depends on Phase 1

`06-view-model.md` defines a single normalized Actual-observation model: point (`at`)
and interval observations, precision, occurrence ordering, multiple-observation
selection/aggregation, and the half-open boundary rule. It defines the comparison
baseline selector, whether deltas are signed, their unit, and behavior for partial or
missing Actuals. `13-presentation-format.md` and `actual-set` schema encode that model.

The same phase closes View/annotation/layout rules: group field addressing; normalized
type/profile selection; explicit time anchors; object endpoint anchoring; explanatory
arrow anchoring; deterministic stable stacking, sort ties, collision handling, and
layout-metrics content/revision contract. Explicit windows MUST have complete bounds.

**Evidence:** comparison truth table; positive and negative Actual/Snapshot/View
fixtures; fixture for one point observation; deterministic layout fixtures with ties;
diagnostics for invalid or ambiguous anchors and grouping.

**Done when:** the UC03 and UC10 outcomes can be derived from written rules alone, and
every View construct has a normalized, deterministic interpretation.

### Phase 3 — Make Style and Theme concrete and deterministic

**Addresses:** R5; depends on Phase 2

`07-style-and-theme.md` defines the closed v0.1 visual vocabulary: legal role
assignments, concrete scalar token types, token definitions, base/variant/extends
resolution, selector precedence, source-order tie breaking, and per-attribute conflict
resolution. It also defines errors for undefined tokens, incompatible values, cycles,
and missing required visual values. Resolve duplicate subsection numbering while
editing.

Update Style and Theme schemas and fixtures to model the closed vocabulary rather than
arbitrary nested maps.

**Evidence:** a fully resolved role-to-concrete-values example and negative fixtures for
undefined token, inheritance cycle, invalid scalar, illegal selector, and unresolved
required property.

**Done when:** identical Project + View + Style + Theme inputs produce the same concrete
appearance values without renderer-specific inference.

### Phase 4 — Specify reactive projection and runtime ordering

**Addresses:** R2 and R4; depends on Phases 1–3

`runtime-reactivity-design.md` separates immutable `evaluationFingerprint` (closure,
engine/package versions, and inputs) from monotonic context-scoped `requestGeneration`
or `contextEpoch`. It defines cancellation, stale result discard, reconciliation,
cache-key, and apply rules.

`08-scene-and-rendering.md` becomes the single owner of a typed, ordered `SceneDelta`:
source/target identities, upsert payloads, removal, ordering, token and viewport
updates, partial replacement scope, and global invalidation reasons. The runtime
document defines impact-set computation; schema and runner validate that a local change
does not upsert or replace unrelated nodes. Global replacement is accepted only for
owner-defined dependency-closure reasons.

**Evidence:** typed delta schema; impact-set matrix; local Actual/annotation change,
View/Theme global-change, and stale-generation fixtures; negative unrelated-upsert and
unsupported-global-reason fixtures.

**Done when:** the reactive UI invariant is mechanically testable: a local semantic
change has a bounded SceneDelta unless the documented impact set justifies otherwise.

### Phase 5 — Close command and transaction contracts

**Addresses:** R7; depends on Phases 1–2

`10-command-model.md` defines the closed v0.1 command registry, payload grammar,
preconditions, diagnostics, transaction envelope, atomic batch semantics, result
shape, undo/redo identifiers, and stale-revision behavior. `13-presentation-format.md`
defines only the persistence/transport envelope that refers to this contract.

Resolve `captureSnapshot` target/store atomicity and Actual resolve/unresolve external
identity restoration. Use discriminated schemas and/or a semantic registry validator;
an unknown command MUST be rejected rather than merely schema-shaped.

**Evidence:** registry table; positive commands; negative unknown-type, invalid payload,
stale revision, partial-batch failure, and external-identity restoration fixtures.

**Done when:** GUI, CLI, and AI can submit the same transaction without any caller
inventing mutation, error, or rollback behavior.

### Phase 6 — Close declarative extension-package resolution

**Addresses:** R8; depends on Phase 1

`11-extension-model.md` defines a versioned package manifest with package/content
identity, compatibility constraints, profiles, fields, constraints, relations, and
derived fields. `05-project-format.md` defines Project package-reference syntax and
normalization. Define graph resolution, inheritance order, cycle diagnostics, conflict
handling, and the boundary preventing extension data from installing arbitrary code or
changing Core scheduling semantics.

**Evidence:** semiconductor package/project fixture that actually resolves; schema and
semantic validation for package identity/version compatibility, missing package,
inheritance cycle, invalid field/relation/derived declaration, and Core-boundary breach.

**Done when:** UC07 is supported through a reproducible declarative package closure and
unknown profiles degrade only by the documented inheritance rule.

### Phase 7 — Build negative conformance and CI evidence

**Addresses:** R10; follows each preceding phase and closes after Phase 6

Expand the presentation manifest to include every positive and negative fixture from
Phases 1–6. The runner must execute structural validation, resource-graph resolution,
owner-semantic validation, and derived SceneDelta assertions. Expected diagnostics are
assertions, not comments. Add the missing View/Style/Theme/Command/profile semantic
checks.

Update CI to install the declared development dependencies and run both the conformance
runner and `pytest`; verify the workflow in its CI environment. If an existing Core
fixture exposes a semantic ambiguity, record an ADR or diagnostic review before
changing the Core specification.

**Done when:** deliberately mutated examples that previously passed (wrong reference,
`git:main`, point Actual, undefined token, unknown command, cyclic profile, unrelated
upsert, incomplete window) fail with the expected diagnostic; CI runs both test layers.

### Phase 8 — Reconcile documentation and repeat final review

**Addresses:** R9 and closure of R1–R10; depends on Phases 0–7

Update the use-case mapping, application/adapter cross-references, quality invariants,
and maturity labels. Verify the review follows one authoritative owner per concept and
that no document contradicts a schema, fixture, or runner. Then conduct a fresh final
cross-document review against the completion gate.

**Done when:** all R1–R10 are closed with linked evidence, deferred items are explicitly
non-goals of minimal implementation, and the renewed review records no gate-blocking
finding.

## 5. Control points

| Control point | Required decision | Exit evidence |
|---|---|---|
| CP1 | Evaluation closure grammar | Revision-bound positive/negative resolution fixtures |
| CP2 | Actual/baseline and View normalization | Comparison truth table and deterministic layout fixtures |
| CP3 | Visual resolution | Concrete role/token resolution fixture |
| CP4 | Reactive projection | Typed SceneDelta and impact-set fixtures |
| CP5 | Mutation contract | Closed command registry and atomic-batch fixtures |
| CP6 | Extension package | Resolved semiconductor package and cycle diagnostics |
| CP7 | Design completion | Full negative conformance, CI evidence, renewed final review |

No later control point may be accepted by assuming an earlier contract. This sequence is
deliberately conservative: shared identities and semantic meanings are settled before
schemas, reactive behavior, or adapters can encode them.

## 6. Completion definition

This remediation program is complete only when all ten finding IDs are marked closed in
their review record, each has linked owner changes and executable evidence, and a new
final review confirms the design-completion gate. At that point — and not before — a
separate plan may authorize minimal implementation.
