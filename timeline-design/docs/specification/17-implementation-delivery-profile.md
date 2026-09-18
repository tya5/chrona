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

This document fixes the package vocabulary only. Workflow-state meaning is owned by the
IDP-2 work package; immutable artifact/evidence reference semantics are owned by IDP-3.
Until those work packages complete, an implementation MUST validate the vocabulary and
field shapes here but MUST NOT infer transition, scheduling, Actual, or resource
resolution behavior from their values.

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
| `workflowState` | `enum` | Yes | one | State vocabulary is deferred to IDP-2. | Declared delivery status metadata only. |
| `artifacts` | `resourceReference` | No | many | Immutable resource contract is deferred to IDP-3. | Inputs or produced delivery artifacts. |
| `acceptanceEvidence` | `resourceReference` | No | many | Immutable resource contract is deferred to IDP-3. | Evidence used to accept a work item or gate. |
| `reuseClassification` | `enum` | Yes | one | Classification vocabulary is deferred to the delivery-review rule. | Declares the intended reuse-review classification. |

An implementation MUST NOT accept these five fields on another profile merely because
their names match. It MUST resolve the package/profile identity first.

## 4. Vocabulary invariants

1. `assignees` references only the two actor profiles in section 2 and is not access
   control or a resource-capacity declaration.
2. `workflowState` and `reuseClassification` are single-valued declarations. They do
   not derive or modify temporal placement, dependencies, calendar choice, Actual, or
   Command authorization.
3. `artifacts` and `acceptanceEvidence` are plural because a delivery item can retain
   more than one immutable input or evidence record. They grant no write authority.
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

Value-level diagnostics for state vocabulary, reference identity/content checks, and
typed-field Commands are introduced only by IDP-2, IDP-3, and IDP-5 respectively.

## 6. Explicit boundary

The only currently valid inference from a delivery profile is that it uses the existing
Core primitive named in section 2. All other delivery metadata is descriptive until its
own profile rule is complete. In particular, `workflowState: completed` MUST NOT be
treated as Actual completion or as a scheduling constraint.
