# Implementation-Delivery Profile Plan

**Status:** Planned prerequisite
**Authority:** This plan owns the completion order for the standard
`implementation-delivery` extension profile. It does not change Core scheduling,
Actual, Command, or Revision Store semantics; those remain owned by specifications
`02`, `04`, `05`, `10`, `11`, `12`, and `15`.

## 1. Purpose

Chrona must be able to express a delivery plan for Chrona itself without inventing a
second project-management model. The missing capability is a bounded standard
extension profile, not a new Core primitive or a generic workflow engine.

The profile will let a Project declare delivery work items and gates with typed:

- assignee references;
- a declared workflow state;
- immutable artifact references;
- immutable acceptance-evidence references; and
- a reuse classification.

It is a prerequisite to the first implementation slice because it is the acceptance
path for self-hosting the delivery roadmap. It remains an extension: the same profile
must also be usable by other Chrona projects.

## 2. Non-negotiable boundaries

1. A workflow state is declarative delivery metadata. It MUST NOT alter temporal
   placement, dependency construction, calendar selection, or Core diagnostics.
2. Workflow state is not `Actual`. Observed execution facts remain in an Actual Set
   and remain subject to the Actual-model resolution rules.
3. Artifact and acceptance-evidence references identify immutable resources through
   the Revision Store contract. They do not grant a Project write authority and do not
   make a mutable branch, working tree, or external URL canonical evidence.
4. The profile may use standard Command families for validated field changes. It MUST
   NOT introduce transition handlers, hidden writes, automation rules, or an opaque
   workflow engine.
5. Reuse classification is delivery-review evidence only. It does not change semantic
   ownership, package compatibility, or the Core/adapter boundary.

## 3. Required design work

| Work package | Required result | Exit evidence |
|---|---|---|
| IDP-1 — Profile vocabulary | **Complete.** Specify profile IDs, allowed base kinds, field schemas, required/optional cardinality, and diagnostic IDs for assignee, workflow state, artifacts, acceptance evidence, and reuse classification. | `17-implementation-delivery-profile.md`, profile schema, and positive/negative vocabulary fixtures. |
| IDP-2 — State and Actual boundary | **Complete.** Specify the finite state vocabulary, its permitted representation, and the rule that it has no scheduling or Actual authority. Specify which state changes are ordinary typed-field Commands. | `17-implementation-delivery-profile.md` state contract plus valid/invalid state and schedule-isolation fixtures. |
| IDP-3 — Immutable evidence boundary | **Complete.** Specify the permitted Revision Store resource-reference kinds and identity/content checks for artifacts and acceptance evidence. Distinguish these from Federation child-export references. | `17-implementation-delivery-profile.md` and evidence-verification fixture reject mutable, kind-mismatched, or content-mismatched references. |
| IDP-4 — Self-hosted roadmap fixture | **Complete.** Encode a representative Chrona delivery plan as a Chrona Project using the profile, including work items, gates, dependencies, evidence, and reuse classifications. | `implementation-delivery-roadmap-v0.1.yaml` validates its profile/evidence vocabulary and schedules deterministically. |
| IDP-5 — Runtime and command integration | **Complete.** Add package resolution, typed-field validation, and standard Command support only to the degree required by IDP-1–4. | Runtime tests validate the self-hosted fixture through Core; CAS field Command creates a content-identified immutable snapshot and rejects invalid/stale changes unchanged. |
| IDP-6 — Review and authorization | Reconcile the profile with Extension Model, Project Format, Command, Revision Store, Quality, and the delivery roadmap. | Cross-document review records owners, diagnostics, deferred functionality, and a published authorization for subsequent slices. |

## 4. Delivery order

IDP-1 through IDP-4 are design and conformance prerequisites. IDP-5 is the first
implementation slice (Slice 0) and may start only after those prerequisites pass.
IDP-6 closes the self-hosting gate before the Revision Store minimum-product work
begins. Each work package is independently validated, committed, immediately
non-force published, and verified on GitHub before the next begins.

## 5. Explicitly not added

This profile does not add assignments as access control, role administration, effort
estimation, resource capacity, cost, tickets, notifications, automatic transitions,
arbitrary external links, DateTime/DST scheduling, or cross-project mutation. Such a
capability needs its own owning-specification change and roadmap decision.
