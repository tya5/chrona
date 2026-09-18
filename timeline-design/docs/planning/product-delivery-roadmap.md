# Product Delivery Roadmap

**Status:** Planned
**Authority:** This document owns delivery order and reuse gates only. Current
specifications `02`–`17` remain the sole authority for semantics and contracts.

## 1. Outcome

This roadmap grows the authorized minimal implementation into the **current designed
Chrona product**: structured project planning, reproducible review/evaluation,
presentation, controlled editing, extension packages, and independently owned
federated timelines. It does not silently promote deferred or undesigned capabilities
into the product commitment.

The key rule is cumulative delivery: a later milestone consumes the same Project,
Revision Store, evaluation, Command, and Scene contracts established earlier. It may
replace an adapter or add a capability, but it must not fork a second semantic model.

## 2. Reuse rules and gates

Every milestone MUST demonstrate all of the following before it is accepted:

1. **Single semantic path** — scheduling, validation, and identity resolution call the
   existing Core/Revision Store services; no UI, CLI, AI, or renderer owns a parallel
   interpretation.
2. **Adapter-only replacement** — an evolved renderer or client may replace only its
   adapter boundary. Project data, Commands, evaluation manifests, diagnostics, and
   Scene identities remain shared.
3. **Executable inheritance** — the full preceding conformance suite remains green;
   milestone-specific tests add evidence rather than replacing earlier tests.
4. **Reuse record** — each completion review classifies changed code as `core`,
   `shared service`, `adapter`, or `experimental`. Experimental code may not become a
   dependency of a later milestone without promotion through the owning specification.
5. **Publish discipline** — one milestone is validated, committed, and non-force
   published before work begins on the next.

## 3. Delivery milestones

| Milestone | End-user outcome | Primary deliverables | Reused unchanged by later work | Exit evidence |
|---|---|---|---|---|
| M0 — Core foundation | A structured Date-only engineering plan can be validated and scheduled deterministically. | Temporal model, schema/semantic validation, scheduler, diagnostics, fixtures. | Core objects, validation, scheduling, diagnostic IDs. | Core conformance and scheduler tests pass. |
| M0.5 — Self-hosted delivery grammar | A team can represent and review its Chrona delivery work as a Chrona Project without changing scheduling or Actual semantics. | Standard `implementation-delivery` profile, bounded typed fields, self-hosted delivery-plan fixture, package resolution and typed-field Command support. | Core scheduling, Actual separation, Revision Store identities, standard Command families, diagnostics. | Profile fixtures prove state isolation, immutable evidence, and deterministic self-hosted plan evaluation; cross-document self-hosting review passes. |
| M1 — Reproducible workspace | A user can evaluate one named immutable local Project revision rather than an ambiguous working file. | Revision Store interface, local snapshot adapter, loader integration. | Resource-reference shape, snapshot identity, content identity. | Repeated evaluation is identical; Draft and stale/mismatched references fail. |
| M2 — Reviewable projection | A user can select a View/Theme/Actual set and obtain a deterministic, traceable SVG projection. | Evaluation manifest, closure resolver, Scene builder, SVG adapter. | Core, Store, Render Context, Scene identities, diagnostics. | Plan/Actual, target capability, local/global SceneDelta fixtures pass. |
| M3 — Controlled change | A user or host can make a semantic change safely and obtain a new immutable revision. | Command executor, transactional local write, undo/redo identity, batch result. | Command envelope, CAS semantics, evaluation invalidation. | Stale revision and partial batch reject atomically; accepted change re-evaluates through the same closure. |
| M4 — Minimal product complete | A user can consume a pinned subproject summary without sharing or mutating its source. | Read-only Federation resolver, trust policy integration, repin flow, aggregate Scene input. | Store, closure, Command, Scene, parent/child authority boundary. | Trust, unavailable export, pin/repin, namespace, and child-mutation denial fixtures pass. |
| M5 — Automation and review | A developer/reviewer can validate, render, and propose the same changes through a supported CLI/automation surface. | CLI adapter, machine-readable diagnostics/results, semantic diff/review presentation. | Command API, Store, validation, scheduler, SVG/Scene pipeline. | CLI output matches library results; no command bypasses the Command Engine. |
| M6 — Interactive review | A user can inspect multiple views and Plan-versus-Actual without a full-scene replacement for a local change. | Read-only interactive adapter, SceneDelta application, accessibility surface. | Render Context, View/Style/Theme, SceneDelta, evaluation cache. | Local-change impact fixtures and accessibility acceptance tests pass in the client. |
| M7 — Interactive editing | A user can edit plans, annotations, Actual reconciliation, and baselines in the interactive client. | Gesture-to-Command adapter, conflict/stale UI, undo/redo UI, annotation editor. | Command executor and transaction results; no direct Project or Scene mutation. | Client emits only valid Commands; conflict and rollback fixtures pass. |
| M8 — Extensible domain product | A semiconductor team can install and use declarative vocabulary/profile packages predictably. | Package registry/acquisition adapter, profile UX, package diagnostics. | The M0.5 profile/package path, Core-boundary rules, Revision Store resolution. | Package compatibility, inheritance, missing/cyclic package diagnostics pass. |
| M9 — Current-design product release | Users can choose supported output targets and work across project views, automation, interactive editing, extensions, and federation. | Target adapters (SVG and approved additional targets), release packaging, end-to-end acceptance suite. | All prior shared contracts; only output/client adapters vary. | Use-case acceptance review covers UC-01–UC-15 at the delivered-adapter level. |

## 4. Boundaries after M9

M9 is the endpoint of the **currently designed** product. DateTime/DST scheduling,
resource leveling, cost/timesheet/ticket management, collaboration/hosted sync,
universal merge, and arbitrary extension code require a new owning-specification change
and a subsequent roadmap amendment before implementation. They are not hidden work
inside any milestone above.

## 5. Milestone reviews

At the end of M2, M4, M7, and M9, conduct a reuse review in addition to feature tests.
It must show that the shared Core/Store/Command/Scene contracts remain the execution
path, list any adapter intentionally replaced, and reject any duplicated semantic
model. This is the control that prevents the minimal implementation from becoming
throwaway code.
