# Implementation-Delivery Profile

**Status:** Draft
**Depends on:** [02 Domain Model](02-domain-model.md), [04 Scheduling Model](04-scheduling-model.md), [05 Project Format](05-project-format.md), [10 Command Model](10-command-model.md), [11 Extension Model](11-extension-model.md), [15 Revision Store Adapters](15-revision-store-adapters.md)
**Owns:** the standard `implementation-delivery` package vocabulary, profile roots,
field ownership, field presence/cardinality, and profile-vocabulary diagnostics.

## 1. Purpose

`implementation-delivery` is a standard declarative package for representing delivery
work in an ordinary Chrona Project. It supplies delivery-management metadata without
adding a Core primitive, scheduling rule, Actual input, authority model, or workflow
engine.

This document fixes package vocabulary and its bounded state declarations. Immutable
artifact/evidence references are shape-only records (section 8). An
implementation MUST validate the vocabulary and field shapes here but MUST NOT infer
scheduling, Actual, or resource-resolution behavior from their values.

## 2. Package and profile identifiers

The package identity is `implementation-delivery`. Its standard profile IDs and Core
inheritance targets are:

| Profile ID | Extends | Purpose |
|---|---|---|
| `implementation-delivery.work-item` | `task` | A temporally scheduled delivery activity. |
| `implementation-delivery.delivery-gate` | `milestone` | A temporally scheduled delivery decision or acceptance gate. |
| `implementation-delivery.person` | `entity` | A named individual eligible for assignment metadata. |
| `implementation-delivery.team` | `entity` | A named team eligible for assignment metadata. |

`work-item` and `delivery-gate` retain every temporal and scheduling rule of their
declared parent. `person` and `team` are ordinary Entities and do not confer identity,
authorization, capacity, or access-control semantics.

## 3. Delivery metadata fields

The following fields are owned independently by both `work-item` and `delivery-gate`.
Field names are package-qualified in a resolved Project even when a compact package-local
serialization is used.

| Field | Type | Required | Cardinality | Declared target / constraint | Meaning at this stage |
|---|---|---:|---|---|---|
| `assignees` | `objectReference` | No | many | `implementation-delivery.person` or `implementation-delivery.team` | Intended delivery ownership metadata. |
| `workflowState` | `enum` | Yes | one | Section 6 state vocabulary. | Declared delivery status metadata only. |
| `artifacts` | `resourceReference` | No | many | `delivery-artifact`; section 8. | Inputs or produced delivery artifacts. |
| `acceptanceEvidence` | `resourceReference` | No | many | `delivery-acceptance-evidence`; section 8. | Evidence used to accept a work item or gate. |
| `reuseClassification` | `enum` | Yes | one | Section 6 classification vocabulary. | Declares the intended reuse-review classification. |

An implementation MUST NOT accept these five fields on another profile merely because
their names match. It MUST resolve the package/profile identity first.

## 4. Vocabulary invariants

1. `assignees` references only the two actor profiles in section 2 and is not access
   control or a resource-capacity declaration.
2. `workflowState` and `reuseClassification` are single-valued declarations. They do
   not derive or modify temporal placement, dependencies, calendar choice, Actual, or
   Command authorization.
3. `artifacts` and `acceptanceEvidence` are plural because a delivery item can retain
   more than one input or evidence record. They grant no write authority.
4. The package contains no Relation profile. Existing Core dependencies remain the only
   delivery ordering mechanism.
5. The package contains no derived field, code plugin, transition declaration, default
   dependent on runtime state, or renderer-specific field.

## 5. Diagnostics

Validators MUST use these stable IDs when the package vocabulary cannot be resolved or
its typed fields violate this specification:

| ID | Condition |
|---|---|
| `IDP-PROFILE-001` | Required `workflowState` or `reuseClassification` field is absent. |
| `IDP-PROFILE-002` | A delivery field appears on a profile other than the two delivery temporal profiles. |
| `IDP-PROFILE-003` | `assignees` does not declare the permitted actor-profile targets or `many` cardinality. |
| `IDP-PROFILE-004` | A single-valued delivery field does not declare `one` cardinality. |
| `IDP-PROFILE-005` | An artifact/evidence field does not declare `resourceReference` with `many` cardinality. |
| `IDP-PROFILE-006` | A standard profile has the wrong parent or an undeclared standard field. |

Every other resolved profile package (#344) is checked against the same field definitions with
generic diagnostics, each pointing at `/objects/<id>/fields[/<name>]`: `E_PROFILE_PACKAGE_INVALID`
(manifest fails `profile-v0.3`), `E_PROFILE_ID_DUPLICATE` (a profile ID declared by two
declared packages, naming both; profile IDs are globally unique per Spec 11; the first declaration stays in
effect and the later package's duplicate is not used), `E_PROFILE_FIELD_UNKNOWN` (field not declared by the object's profile),
`E_PROFILE_FIELD_TYPE` (value is not the declared scalar, array or reference shape),
`E_PROFILE_FIELD_ENUM` (value outside `enumValues`) and `E_PROFILE_FIELD_REQUIRED` (required field absent
or null). An absent optional field is valid and an explicit `null` is valid only for an optional field.
`E_EXTENSION_UNRESOLVED` (a `path` extension whose file is missing, escapes the Project directory or is not a
YAML mapping; pointer `/extensions/<i>/path`) and `E_CONTENT_IDENTITY` (declared `contentIdentity` differs
from the file bytes) are reported by the same checker. It runs wherever a Project is validated: `chrona validate`,
`schedule`, draft `render`, the MCP `validate_project`/`schedule_project`/`render_draft` tools and Context
render (#1682). `path` is resolved beside the Project file; a local file that omits `contentIdentity` takes the
SHA-256 of its bytes. `resource` declarations need a Store and are resolved by the Context path.
A field definition may declare an optional `default` (a value of its declared scalar type; not for reference or
many-valued fields; a non-conforming default is `E_PROFILE_PACKAGE_INVALID`). The source-local field accessor (`FieldRoleBindings.read_result`, one per source Project, so Snapshot, scenario, row and folded occurrences alike) reads the default when the
field is absent from an object of that profile, and Style predicates and View encodings both see it (an explicit `null` stays `null` and is a value-less object for a colour encoding), and an absent `required` field with
a default is satisfied. `default` is an additive optional `profile-v0.3` member (Spec 56 section 3.2). A colour encoding
(Spec 60) on a field for which an object has no value (its declared profile does not declare the field, the field is
absent without a default, or the value is `null`; #1682, #1789) does not apply to that object: it keeps its
base paint and the legend's base key stays, unless the encoding's optional `missing` names a domain value. A value
that is present but outside the domain is still refused with `E_PRESENTATION_SCALE_VALUE`.
Objects whose `type` names no declared profile are not checked. The delivery package keeps its `IDP-*` codes.
Within one Project, two declared packages MUST NOT claim the same profile ID
(Spec11 §4.1). Report `E_PROFILE_PACKAGE_INVALID` at the conflicting extension;
declaration order MUST NOT silently choose a field schema. Independent source
Projects resolve their own packages and descriptor catalogues.

Typed-field Command execution is introduced by IDP-5. Evidence references are validated
for shape only (section 8).

## 6. State and reuse declarations

`workflowState` has exactly one of these values:

| Value | Meaning |
|---|---|
| `planned` | The delivery item is intended but not claimed to be active. |
| `active` | The delivery item is currently being worked. |
| `blocked` | The delivery item cannot currently proceed. |
| `completed` | The delivery item is claimed complete for delivery tracking. |
| `cancelled` | The delivery item is no longer intended to proceed. |

`reuseClassification` has exactly one of `core`, `shared-service`, `adapter`, or
`experimental`. It records the classification required by the delivery reuse review;
it does not itself approve promotion or change the semantic owner of code.

The permitted state values are declarations, not executable transitions. A state change
is an ordinary validated `setTypedField` Command using the standard base-revision and
atomicity rules. There is no package-supplied transition graph, guard, actor permission,
notification, automatic update, or derived write. Hosts MAY present a state transition
in an adapter, but the adapter MUST submit the same ordinary Command and cannot claim a
different semantic result.

Validators MUST diagnose an enum value outside these vocabularies as `IDP-STATE-001`.
An attempt to use a state declaration as a temporal/dependency input or as an Actual
observation is `IDP-STATE-002`.

## 7. Explicit boundary

The only scheduling inference from a delivery profile is that it uses the existing Core
primitive named in section 2. In particular, `workflowState: completed` MUST NOT be
treated as Actual completion or as a scheduling constraint. A Project whose delivery
metadata differs only in `workflowState` or `reuseClassification` therefore has the
same scheduling inputs, schedule, and Core diagnostics.

## 8. Artifact and acceptance evidence references

Each `artifacts` entry MUST be a Revision Store resource reference with kind
`delivery-artifact`; each `acceptanceEvidence` entry MUST be one with kind
`delivery-acceptance-evidence`. The reference carries its Store identity, address,
opaque revision token, and SHA-256 content identity. These references are shape-only
records: chrona validates the reference's shape against the Revision Store resource
reference schema and its kind against the field, and does not open, resolve, or verify
the target. In particular it does not check that the revision token names an immutable
Snapshot, nor that the stored bytes, stable ID, or kind match the reference. Profile
logic MUST NOT parse a provider token to guess mutability.

`timeline-export` is a Federation-only kind and MUST NOT appear in either field. A
delivery artifact/evidence reference grants no read-through child Project semantics and
no mutation authority. `IDP-EVIDENCE-001` diagnoses a reference that violates the
Revision Store resource reference shape; `IDP-EVIDENCE-002` diagnoses a field/kind
mismatch. The `verification` flags in the conformance fixture
`conformance/implementation-delivery-evidence-v0.1.yaml` are declared inputs to the
conformance harness, not results computed by chrona.

Revisit condition: open and verify an evidence reference only when a feature consumes
evidence (for example automated acceptance); that feature opens it through the shared
Store address guard and verifies `contentIdentity`, and updates this section together
with `tests/unit/tools/test_evidence_reference_spec.py`.
