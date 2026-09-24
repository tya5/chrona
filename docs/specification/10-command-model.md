# Command Model

**Status:** Draft
**Depends on:** [02 Domain Model](02-domain-model.md), [04 Scheduling Model](04-scheduling-model.md), [06 View Model](06-view-model.md), [09 Application Architecture](09-application-architecture.md), [15 Revision Store Adapters](15-revision-store-adapters.md)
**Owns:** canonical mutation interface, command preconditions and results, validation and transaction boundaries, undo/redo semantics, and the relationship between semantic changes and Revision Store snapshots.

## 1. Purpose

A **Command** is a typed, declarative request to create a new canonical Chrona revision. CLI clients, interactive editors, automation, and AI agents use the same Command Model. No client changes a Project by editing a scheduler result, Scene, SVG, or canvas store directly.

A Command expresses an intended semantic or View-definition change; it is not a renderer event, JSON Patch, arbitrary script, or instruction to adjust pixels until a diagram appears correct.

```text
CLI / GUI / AI / automation
            ↓
      Command request
            ↓
Validation + transaction
            ↓
  New canonical revision
            ↓
 Rebuild schedule and presentation
```

## 2. Invariants

- A command MUST name its target canonical store and bind to a base revision or equivalent concurrency precondition.
- A rejected command MUST leave canonical state unchanged.
- A successful command MUST create an identifiable new revision and report the normalized semantic change it made.
- Command execution MUST validate the owning semantic specification; a UI, AI agent, or renderer cannot override scheduling authority.
- A command MUST NOT write derived schedule placements, Scene coordinates, SVG, or canvas-store state as canonical Project data.
- Actual observations MUST remain independent observations. Recording or editing one MUST NOT implicitly reschedule planned work.
- Semantic dependencies and presentation-only explanatory arrows MUST be mutated by distinct command families.
- Command payloads and declarative predicates MUST NOT execute arbitrary host-language code.

## 3. Command envelope

Every command request has the following conceptual fields. Concrete JSON, YAML, CLI, RPC, and UI transport syntax is deferred.

| Field | Meaning |
|---|---|
| `commandId` | Client-generated identity for tracing and idempotent retry within an execution scope |
| `type` | Versioned command kind |
| `target` | Project, named Actual input, View definition, or other explicitly identified canonical store |
| `baseRevision` | Revision the client inspected, or an equivalent declared precondition |
| `payload` | Typed command-specific intent using stable IDs and declared values |
| `actor` | Optional caller identity and provenance metadata |
| `reason` | Optional human-readable intent for review and AI traceability |

`baseRevision` is the opaque revision token issued by the target Revision Store. It is
mandatory for canonical mutation unless the target store explicitly provides an
equivalent compare-and-set condition. A Command Engine passes it unchanged to the Store;
it must not parse, fabricate, or assume Git syntax. A command must not silently apply to
an arbitrary working-tree tip.

The closed `authoring-command/v0.1` family is a target-specific equivalent
condition, not a Revision Store command: its `baseRevision` is the canonical
content identity of the validated local authoring workspace. Specification 51
owns that file-local rule and its public revision-read operation. It does not
alter the opaque Store-token rule for this Command Model or the
`command/v0.2` operational profile in Specification 35.

### 3.1 v0.1 serialized request document

Command documents are transport or review inputs, never members of the Presentation
resource graph. Their YAML/JSON form is deliberately separate from the resource
envelope:

```yaml
# chrona-contract: historical
version: chrona/command/v0.1
commandId: 0195b5d1-actual-edit
type: editActualObservation
target:
  kind: actual-set
  id: controller-observed
  path: actuals/controller-observed.yaml
baseRevision: git:4f2c9ab
payload:
  observationId: observed-firmware
  actual: {finish: 2026-04-18, progress: 0.75}
reason: supplier confirmation
```

`type`, `target.kind`, and `payload` are a closed registry owned by this specification.
The document has no resource `kind` or resource `id`; `commandId` supports idempotent
retry but does not make the request canonical state. A batch is a separate document
with one target/base-revision scope and an explicit ordered `commands` list. It is not
an implicit sequence of files or a GUI undo stack.

### 3.2 Closed v0.1 registry

| Type | Target kind | Required payload | Result boundary |
|---|---|---|---|
| `editActualObservation` | `actual-set` | `observationId`, non-empty `actual` | Replaces only that observation's Actual fields |
| `resolveActualObservation` | `actual-set` | `observationId`, `projectObjectId` | Preserves external identity in execution record |
| `unresolveActualObservation` | `actual-set` | `observationId`, `externalIdentity` | Restores explicit unmatched external identity |
| `captureSnapshot` | `project` | `snapshotId` | Atomically creates immutable Snapshot bound to target base revision |
| `setTypedField` | `project` | `objectId`, `field`, `value` | Replaces one declared profile-owned field on one stable Project object |
| `addPresentationAnnotation` | `view` | complete `annotation` | Adds one View-local annotation with a stable ID |
| `editPresentationAnnotation` | `view` | `annotationId`, complete replacement `annotation` | Replaces one View-local annotation; IDs must agree |
| `deletePresentationAnnotation` | `view` | `annotationId` | Deletes one View-local annotation only |

The `annotation` payload is exactly the v0.1 presentation-annotation intent defined by
the View Model: a stable ID, permitted purpose, typed anchor (or typed source/target
for an explanatory arrow), logical placement, and text. It cannot carry Scene offsets,
renderer geometry, or a Project mutation. `editPresentationAnnotation` replaces the
complete intent rather than applying an untyped patch; its `annotationId` and
`annotation.id` MUST be equal.

`baseRevision` is the opaque token issued by the targeted Store. Examples may use a
Git token, but the command schema MUST NOT constrain the token syntax to Git.

`setTypedField` is the serialized project-field form used by CLI, automation, GUI, and
AI proposal adapters. `objectId` is a stable Project object ID, never a title or Scene
ID. `field` names one field declared by the resolved profile/package closure and
`value` is validated by that declaration. The command cannot alter object identity,
Core type, placement mode, resolved schedule, derived field, renderer state, or an
undeclared field. The Command Engine loads the declared package closure and validates
the candidate through the same profile and scheduling path as every other project
Command before its compare-and-set write.

Unknown types, wrong target kinds, unknown payload fields, and stale base revisions are
rejected. A transaction has one target and base revision plus an ordered, non-empty
command list; it is all-or-nothing and produces one result revision.

### 3.3 Federation registry (post-v0.1)

Federation is not back-ported into the closed v0.1 command registry. Its separately
versioned request document is `chrona/federation-command/v0.1` and has exactly two
types:

| Type | Target kind | Required payload | Result boundary |
|---|---|---|---|
| `pinFederatedExport` | `federation-plan` | `federationId`, complete immutable `export` reference, `presentation` | Replaces one parent-side pinned reference only |
| `unpinFederatedExport` | `federation-plan` | `federationId` | Removes one parent-side reference only |

Both require a Federation Plan base revision. Validation resolves the candidate export
before persisting the new plan revision and rejects untrusted repositories, branch tips,
kind/project-ID mismatch, namespace collision, duplicate federation ID, or cycle. No
Federation Command has a child Project target or a payload capable of editing child
source, source schedule, or export contents.

The v0.1 YAML examples retain `git:<sha>` as a legacy Git-adapter token. Successor
command documents use `revision-store-resource-ref-v0.1.schema.yaml` for their target
and preserve the Store-owned revision token without changing Command semantics.

## 4. Command families

### 4.1 Project structure and fields

| Family | Intent | Examples |
|---|---|---|
| Create | Add a typed semantic item with a stable ID | `createObject`, `createEntity`, `createRelation`, `createSemanticAnnotation` |
| Update | Change a permitted typed semantic field | `setObjectField`, `setEntityField`, `setProjectField` |
| Remove | Remove a semantic item under explicit reference-integrity rules | `deleteObject`, `deleteEntity`, `deleteRelation`, `deleteSemanticAnnotation` |
| Profile / schema use | Assign or change an already supported profile or typed field value | `setProfile`, `setTypedField` |

Commands operate on stable IDs, never on visible title text, array position, Scene ID, or a renderer-selected shape. The Extension Model defines what profiles and fields are legal; this document does not authorize an untyped catch-all mutation mechanism.

### 4.2 Temporal placement and scheduling constraints

`moveTemporalObject`, `resizeTemporalSpan`, `setPlacementMode`, `setScheduleAnchor`, and `setBound` are semantic requests. Their meaning depends on the object's placement mode and profile:

| Placement mode | Permitted command effect |
|---|---|
| Fixed | Update authoritative fixed endpoint(s), subject to temporal validation |
| Scheduled with explicit anchor | Update the declared anchor or other allowed scheduling constraint; re-evaluate the schedule |
| Scheduled without explicit anchor | Add, change, or remove an allowed constraint/anchor; do not write a resolved placement as if fixed |
| Derived | Change the derivation declaration or its source semantics; direct move/resize of the derived result is rejected |

The Command Engine delegates feasibility and authority checks to the Scheduling Model. It must reject, rather than silently move, fixed targets or explicit anchors when a dependency or bound conflicts. A command result may include a newly derived schedule for inspection, but that schedule is not the command's persisted mutation.

### 4.3 Relationships and annotations

`createDependency` and `deleteDependency` mutate semantic Relations with explicit endpoints and dependency profile semantics. They therefore undergo scheduling validation.

`addPresentationAnnotation`, `editPresentationAnnotation`, and `deletePresentationAnnotation` mutate a View-local annotation definition. An explanatory arrow is created through this family, not through dependency creation. Its stable anchors and logical placement preferences may be changed, but its concrete Scene offsets and routed path are derived state.

`resolveActualObservation` and `unresolveActualObservation` mutate only the explicit
alignment of a named Actual observation. Resolution requires a supplied stable
`projectObjectId`; unresolution restores an external identity with `alignment:
unmatched`. Neither command may infer an ID from title similarity or alter planned data.

Semantic annotation commands mutate Project annotations; presentation annotation commands mutate the named View definition. Neither family may be used to create an undeclared scheduling constraint.

### 4.4 Actual and Snapshot inputs

When a named Actual input store is available, `recordActualObservation`,
`editActualObservation`, and `removeActualObservation` mutate that independently
identified store. An observation MAY carry either a resolved stable Project object ID or
an external observation identity with an explicit `unmatched` alignment state. A
resolved Project object ID must validate; an unmatched observation is accepted with a
diagnostic and is never matched by title similarity. This permits imported or newly
recorded facts to be reviewed before alignment. These commands do not change planned
dependencies, planned duration, forecast, or schedule.

Snapshot capture, selection, and persistence syntax remain deferred. A command may reference a named immutable Snapshot only where its future store specification permits it; no command may reinterpret a mutable Project revision as a Snapshot without an explicit capture operation.

`captureSnapshot` creates a `snapshot-ref` whose Project reference is the exact target
revision inspected by the command. It rejects a moving branch name or an unstated tip.
The result names the new immutable Snapshot resource; capture never copies derived
schedule or Scene data into it.

## 5. Validation and execution

Commands are processed in this order:

1. validate envelope shape, target identity, command type, and base revision;
2. validate authorization and caller policy at the application boundary where required;
3. load the target revision and validate referenced stable IDs and typed fields;
4. apply the requested mutation to an isolated candidate state;
5. validate profile, temporal, relation, and View invariants;
6. run required scheduling-feasibility validation for semantic changes that affect it;
7. normalize the accepted canonical representation and compute the semantic change set;
8. atomically persist the new revision, invalidate derived outputs, and return the result.

Validation must use the same Core and presentation specifications regardless of client. A GUI may give an early affordance warning and an AI may request a dry run, but neither result substitutes for final Command Engine validation.

## 6. Command result

A command result is explicit about success or rejection.

| Field | Success | Rejection |
|---|---|---|
| `status` | `accepted` | `rejected` |
| `commandId` | Echoed | Echoed |
| `baseRevision` | Echoed | Echoed |
| `resultRevision` | New canonical revision identity | Absent |
| `changes` | Normalized semantic/View change set | Empty |
| `diagnostics` | Informational/warning diagnostics and optional derived preview | Validation failures and conflicts |
| `invalidated` | Derived artifacts no longer valid | Empty |

The change set is structured by stable IDs and owning fields so it can be rendered as a meaningful Git diff. It is not required to preserve incidental YAML formatting or a renderer's internal operation history.

The table above describes Store command results. The authoring-workspace
equivalent precondition uses the separate `authoring-command-result/v0.1`
contract: it reports `commandBaseRevision`, the observed
`workspaceRevision`, and `resultRevision`, so a rejected workspace command
never mislabels the observed revision as an echoed input.

## 7. Transactions, batches, and concurrency

A transaction is an ordered list of commands evaluated against one base revision. The transaction is atomic: either all commands are accepted and produce one canonical revision, or none are persisted. Command order is explicit and visible in the transaction result.

Commands within a transaction see the candidate state produced by preceding commands. Final semantic and scheduling validation applies to the completed candidate state, so a valid intermediate form may be temporarily incomplete only inside the isolated transaction; it must not be externally observable or persist on failure.

For concurrent writers, the Project Store compares `baseRevision` with the canonical tip. On mismatch, it rejects the command with a conflict diagnostic or performs a separately specified explicit merge. It MUST NOT use hidden last-writer-wins semantics. An accepted `commandId` may be retried idempotently only when its target and payload are identical to the recorded execution.

## 8. Undo and redo

Undo and redo are Commands that create new revisions; they do not rewrite shared history or mutate a renderer-local stack.

- An accepted command records sufficient normalized prior state or inverse intent to construct a reversible operation where one exists.
- `undo` targets a specific accepted command or transaction and is evaluated against the current revision, with normal validation and conflict checks.
- If later changes make a clean inverse unsafe, undo is rejected or requires an explicit resolution command; it must not overwrite unrelated edits.
- `redo` reissues the previously undone semantic intent against an explicit base revision and is subject to the same validation as a new command.
- Non-reversible operations, including deletion after external reference changes or snapshot operations with immutable semantics, declare that limit in their result rather than pretending to support undo.

Git remains the durable history mechanism for canonical files. Command history augments it with intent, validation, and client-independent undo/redo semantics; it is not a replacement for Git commits, branches, or review.

## 9. Client integration and AI operation

Client adapters translate user gestures or natural-language intent into a previewable Command request. Before submission, a client MAY show the target IDs, base revision, requested semantic fields, predicted diagnostics, and expected derived-view effect.

AI agents use the same typed command vocabulary and base-revision checks as other clients. They may not submit raw source rewrites as a way to bypass validation, nor may they turn an uncertain title match into an object reference without obtaining a stable ID or producing an ambiguity diagnostic.

Authorization, approvals, and policy enforcement are application concerns, but an authorization decision must be applied before persistence and recorded in the result provenance where applicable. They must not change the semantic meaning of an accepted command.

### 9.1 AI proposal and authorization exchange

An AI client submits `chrona/ai-command-proposal/v0.1`, not a source rewrite. Its
`proposedCommand` MUST validate against the closed Command registry and preserves the
original `commandId`, target, and base revision. The proposal records the authenticated
principal, agent identity, model identity, and a reviewable intent. It cannot contain
arbitrary source text, executable code, a renderer edit, or an inferred title match.

The application boundary computes a canonical SHA-256 command fingerprint and emits a
separate `chrona/authorization-decision/v0.1`. An `allow` decision binds exactly one
proposal, principal, policy version, and fingerprint. A changed payload, target, base
revision, or principal invalidates the decision; `deny` never persists a Command.
The Command Engine performs normal semantic validation and compare-and-set after an
allow decision, so authorization never substitutes for validation or permits a stale
write. The resulting provenance retains proposal ID, fingerprint, and policy version.

## 10. Resource-leveling successor commands

The closed v0.1 registry is unchanged. The separately versioned resource-capacity
successor adds a two-step command boundary:

| Type | Target kind | Required payload/result | Mutation boundary |
|---|---|---|---|
| `evaluateResourceLeveling` | `project` | explicit capacity-set reference, objective, movement scope; derived proposal and diagnostics | No canonical mutation |
| `applyLevelingProposal` | `project` | `proposalId`, evaluated revision/fingerprint, selected proposed semantic changes | One normal Project revision |
| `recordCostObservation` | `cost-observation-set` | independently identified rate/timesheet/cost observation | Cost observation revision only |

`evaluateResourceLeveling` is not a convenience write. Its result is bound to the
Project and capacity revisions used for evaluation and uses the declared stable
tie-break rule after the declared objective. `applyLevelingProposal` validates its
current `baseRevision`, the referenced evaluation fingerprint, fixed-placement and
bound rules, and all normal scheduling constraints. A stale or selectively copied
proposal is rejected. Cost and timesheet commands cannot target a Project or cause a
schedule invalidation except for a separately requested display evaluation.

## 11. Collaboration successor commands

The collaboration successor wraps an existing typed semantic Command in
`submitCommand`, retaining the original target and base revision. The application
records actor/policy provenance and any approval fingerprint, but these metadata do not
alter command semantics. `resolveMergeConflict` names one durable conflict object,
all parent revisions, and an allowed typed resolution; it then follows the ordinary
validation and Store write path. Neither command accepts a raw patch, Scene mutation,
or implicit merge preference.

## 12. Progressive authoring successor commands

[51 Progressive Authoring](51-progressive-authoring.md) adds a separately versioned,
closed workspace command registry. `setWorkspaceTask`, `setWorkspaceActual`,
`selectPresentationPreset`, and `setPresentationOverride` have an
`authoring-workspace` target and validate the complete normalized candidate. They do
not admit arbitrary source patches, Project/Actual mutation through a presentation
path, renderer state, or Scene geometry.

`materializePresentationPreset` is the one successor aggregate transaction. Its target
names the workspace and all generated explicit-resource destinations, and its opaque
base revision covers that complete aggregate. The Engine resolves the exact preset and
binding, validates the whole candidate and byte-equivalence proof, then commits all
named resources and its receipt or none. It rejects stale bases and destination
collisions. Its receipt is provenance, not a canonical input or inheritance fallback.
This successor deliberately does not change the v0.1 one-target serialized registry.

## 13. Out of scope

This document does not define:

- wire formats, CLI syntax, HTTP/RPC endpoints, GUI widgets, or AI prompt formats;
- alternate transport, CLI, RPC, or GUI wire encodings beyond the v0.1 serialized request document;
- profile-extension semantics, custom command registration, or code-plugin APIs;
- service authorization policy, identity provider, or approval UX;
- Git branching/merge policy or repository hosting workflow; or
- direct editing/import of SVG, Scene, or tldraw store state as canonical data.

## 14. Boundary to Extension and Quality specifications

[11 Extension Model](11-extension-model.md) determines which profile- and field-level changes are legal and how extension-provided command kinds, if any, remain declarative and safe. [12 Quality and Invariants](12-quality-and-invariants.md) supplies cross-system properties against which command processing is tested. New command kinds that alter Core semantic authority, scheduling behavior, or renderer round-tripping require a specification review and normally an ADR before implementation.
