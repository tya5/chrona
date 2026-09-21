# Operational Review Workflows

**Status:** Proposed  
**Depends on:** [09 Application Architecture](09-application-architecture.md),
[10 Command Model](10-command-model.md), [12 Quality and Invariants](12-quality-and-invariants.md),
[13 Presentation Format](13-presentation-format.md), and [15 Revision Store Adapters](15-revision-store-adapters.md).  
**Owns:** external Actual intake/reconciliation, revision-bound automation, named
baseline capture/comparison, their resource contracts, and CLI/CI behavior.

## 1. Purpose and authority

This specification makes UC-10, UC-11, and UC-12 product-operable without granting a
connector, working tree, renderer, or CI runner authority over canonical semantics.
All input closures are explicit immutable Revision Store resource references. A path may
locate a submitted document on the client machine, but it is never a selector for a
Chrona Project, Actual-set, baseline, or store tip.

An Actual is an observed fact, not a forecast. Intake may create an unmatched
observation but MUST NOT change a Project, schedule, View, Scene, or baseline.
Reconciliation is the separately auditable operation that assigns an exact stable
Project object ID. Baseline capture records an already inspected Project revision; it
does not copy a schedule or rendered output.

## 2. Immutable references and stores

Every M26 target, output artifact, and baseline Project is a
`revision-store-resource-ref/v0.1` as defined by
`revision-store-resource-ref-v0.1.schema.yaml`. The Command Engine verifies its Store,
address, kind, ID, opaque revision token, and content identity before execution.

A **baseline registry** is an append-only Revision Store resource namespace. It
supports `verify(ref)`, `read(snapshot, address)`, and `publish(address, bytes)` with
create-if-absent semantics. `publish` either makes the complete normalized resource
durably readable or leaves no resource. A local adapter stores one canonical YAML file
per address; its configured registry identity is part of every output reference.

## 3. External Actual intake (UC-10)

### 3.1 Batch resource

`chrona/actual-intake-batch/v0.2` is an immutable resource document validated by
`actual-intake-batch-v0.2.schema.yaml`. Its `kind` is `actual-intake-batch`; source and
records live in `body`. It has one source and an ordered list of records. `source.system` and each `externalKey` form the stable external fact
identity. `source.contentIdentity` is the SHA-256 identity of the exact normalized
source payload from which the adapter produced this batch. `source.locator`, when
present, is audit text only and MUST NOT be fetched by Chrona.

`actual-intake-batch/v0.1` is an unreferenced historical transport shape. M26 commands
reject it; they do not up-convert bytes, invent a resource identity, or read a batch
from a raw CLI path.

The initial profile accepts already-normalized Date-only Actual fields only. A Command
payload carries a complete immutable `actual-intake-batch` reference; the Engine
verifies it before accessing `body.source` or `body.records`. Source
parsers, HTTP clients, credential storage, webhook handling, and automatic identity
matching are deliberately out of scope.

### 3.2 Apply and reconcile operations

`applyActualIntakeBatch` targets an immutable `actual-set/v0.2` reference and carries an
immutable batch reference. Its target revision and content identity are the required
CAS precondition. The engine validates the batch before loading the Actual-set, then
processes records in their declared order. A supplied `projectObjectId` is accepted
only if it is an exact ID in the Project reference supplied by the command payload;
otherwise the new observation is stored with `externalIdentity` and
`alignment: unmatched`. No title, label, position, or source URL is used for matching.

The external fact key is `(source.system, externalKey)` and MUST be unique both within
the batch and within the target Actual-set. Actual-set v0.2 stores the normalized
`sourceContentIdentity` alongside every externally identified observation; its schema is
`actual-set-v0.2.schema.yaml`. An existing fact with byte-equivalent normalized Actual
fields and the same source content identity is an idempotent no-op.
An existing fact with different Actual fields or a different source content identity is
rejected as `E_ACTUAL_EXTERNAL_CONFLICT`; an operator must use the explicit
`editActualObservation` command. A successful non-no-op batch creates one Actual-set
revision. A batch containing any invalid/conflicting record creates none.

`resolveActualObservation` remains the only operation that changes an unmatched fact
to a resolved Project ID. It requires the same immutable Actual-set and Project
closure and rejects a stale revision, unknown observation, non-unmatched observation,
or unknown Project object. In Actual-set v0.2, resolution adds `projectObjectId` while
retaining `externalIdentity` and `sourceContentIdentity`; it removes only
`alignment: unmatched`. `unresolveActualObservation` removes the Project ID and
restores that alignment. Neither operation changes observed fields or external
provenance.

### 3.3 Intake report

The command result includes an `actualIntake` report with `batch`, `source`, and one
ordered per-record disposition: `inserted`, `alreadyPresent`, or `rejected`. A rejected
command has no `resultRevision`; its report exposes all deterministic validation
diagnostics but never a partial candidate. Accepted reports have `rejected: 0`.

| Code | Meaning |
|---|---|
| `E_INTAKE_SCHEMA` | batch or normalized Actual is invalid |
| `E_INTAKE_DUPLICATE_KEY` | duplicate `(system, externalKey)` in batch or target |
| `E_INTAKE_SOURCE_IDENTITY` | source identity is absent, malformed, or conflicts on replay |
| `E_ACTUAL_EXTERNAL_CONFLICT` | an existing external fact differs from the submitted fact |
| `E_INTAKE_PROJECT_REFERENCE` | supplied Project closure is missing or does not contain the exact ID |

## 4. Revision-bound automation (UC-11)

### 4.1 Command v0.2

`chrona/command/v0.2` replaces v0.1 for this operational profile. It contains
`commandId`, `type`, immutable `target`, `baseRevision`, `expectedContentIdentity`,
typed `payload`, optional `actor`, and optional `reason`. `baseRevision` MUST equal
`target.revision.token`; `expectedContentIdentity` MUST equal `target.contentIdentity`.
The target never has a raw `path` field. A payload reference is immutable and verified
before use. Commands are not Presentation resources.

The v0.2 registry is closed: `applyActualIntakeBatch`, `editActualObservation`,
`resolveActualObservation`, `unresolveActualObservation`, `captureSnapshot`, and
`setTypedField`. The legacy v0.1 registry remains readable only for its published
scope. `propose-set` is removed during implementation: `command-check` is validation
only and `command-apply` is the sole mutation entry point.

An accepted replay has the same `commandId`, canonical request content identity,
target reference, and result identity as the recorded execution. It returns the
original result with `replayed: true` and performs no write. Reuse of a command ID with
any other canonical request is `E_COMMAND_ID_REUSE`.

### 4.2 Automation result

Every `command-check`, `command-apply`, intake, capture, and comparison invocation
emits `chrona/automation-result/v0.1`, validated by its schema. A result records its
operation, request content identity, status, complete verified input closure, ordered
diagnostics, and declared artifacts. Accepted mutations also name `resultTarget`;
checks and rejections do not fabricate it. Console text is never an automation API.

The CLI exits `0` for accepted work (including an accepted replay), `2` for a declared
rejection, and `3` only when the runner cannot construct or write its requested result
artifact. Schema-valid results are still written for exit `2`; no result is promised
for process interruption before output publication.

## 5. Named baselines (UC-12)

### 5.1 Capture

`captureSnapshot` v0.2 targets an immutable Project reference and has a `snapshotId`
that is a valid stable resource ID. The engine verifies the target closure, then
publishes a `chrona/snapshot-ref/v0.2` resource at the registry's canonical
`snapshots/<snapshotId>.yaml` address. Its body contains exactly the verified Project
reference. The registry creates it once only. Existing IDs reject with
`E_BASELINE_EXISTS`, even when their contents are identical. The operation is
non-reversible and does not mutate the Project.

`payload.registry` is an output Store selector `{provider, identity}`, not a resource
reference: capture creates the first resource in that namespace, so no immutable
registry resource exists to verify beforehand. The configured Store must resolve the
selector exactly; the accepted result names the created immutable snapshot reference.

### 5.2 Compare

`baseline-compare` receives an immutable snapshot-ref reference and an immutable
candidate Project reference. It verifies the snapshot resource and the Project
reference nested within it, then verifies the candidate independently. The resulting
semantic review uses the existing revision comparison model and records both closures
in the automation result. It does not compare rendered pixels, current filesystem
contents, branch names, or clocks. A baseline and candidate may be in different Stores
only when both explicit references independently verify.

| Code | Meaning |
|---|---|
| `E_AUTOMATION_TARGET_CLOSURE` | target/reference Store, ID, kind, revision, or content identity fails verification |
| `E_AUTOMATION_BASE_REVISION` | command precondition disagrees with target revision |
| `E_COMMAND_ID_REUSE` | a previously recorded command ID has different request bytes or closure |
| `E_BASELINE_EXISTS` | baseline registry already has the requested ID |
| `E_BASELINE_REFERENCE` | snapshot resource or embedded Project reference is invalid/unreadable |
| `E_AUTOMATION_OUTPUT_EXISTS` | a requested output artifact already exists or cannot be atomically published |

## 6. CLI and CI contract

`--store-config` is a `chrona/store-config/v0.1` document. Each entry maps exactly one
declared `(provider, identity)` to a local adapter root. Duplicate pairs reject before
any operation. The initial product profile permits only `provider: local`; `root` is a
client transport location and has no authority to alter the reference's provider,
identity, address, revision, or digest. Credentials are not representable in this file.
Future credential-bearing providers require a new versioned config format and ADR.

For a local writable Actual Store, an immutable Actual-set reference resolves as
`<root>/<revision-token>/<address>`, with `address: actuals/<id>.yaml`. The only mutable
adapter state is the non-input pointer `<root>/actual-tips/<id>.json`. An apply first
compares that pointer with `target.revision.token`, writes a complete new token
directory, then atomically advances the pointer. The pointer, root default, and latest
token are never accepted in a command document. Store provisioning creates the first
pointer out of band from a verified immutable Actual-set reference; a missing pointer
is a rejection, not an implicit bootstrap write.

| Command | Required inputs | Mutation | Output |
|---|---|---|---|
| `chrona command-check` | `--command`, store configuration, `--result` | none | atomic result file |
| `chrona command-apply` | same as check; writable named Store | declared target only through CAS | atomic result file |
| `chrona actual-intake` | v0.2 intake command | Actual-set only through CAS | result with intake report |
| `chrona actual-resolve` | v0.2 resolution command | Actual-set only through CAS | result |
| `chrona baseline-capture` | v0.2 capture command, writable registry | registry create-if-absent only | result naming baseline reference |
| `chrona baseline-compare` | `--baseline-reference`, `--candidate-reference`, `--result` | none | result with semantic comparison artifact |

`--result` is an explicit empty destination. The client serializes a complete result to
a sibling temporary file, fsyncs where supported, and renames once; it MUST reject an
existing destination. CI passes only immutable input references and configured Store
identities. Secrets are supplied by the Store adapter's process environment or external
credential provider; they are never placed in command, batch, baseline, result, or
Project documents.

## 7. Required evidence

Implementation must add schema and runtime evidence for accepted intake, duplicate
batch key, conflicting replay, unmatched/exact resolution, stale command, command-ID
reuse, atomic result collision, baseline capture collision, cross-store comparison,
and no-working-tree CI. All output results must be canonicalized before their content
identity is calculated.
