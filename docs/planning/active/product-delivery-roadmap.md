# Product Delivery Roadmap

**Status:** Planned — design authorization renewed
**Authority:** This document owns delivery order and reuse gates only. Current
specifications `02`–`17` remain the sole authority for semantics and contracts.

TR-2 assigns milestone ownership for UC-06, UC-10, UC-16–UC-21, and the FD-1–FD-5
successor designs. TR-3 validates the complete traceability matrix and TR-4 renews the
whole-system design review. Each implementation milestone remains independently gated
by its declared conformance and reuse evidence.

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
| M0.5 — Self-hosted delivery grammar | A team can describe its Chrona delivery work as a Project without changing scheduling or Actual semantics. | Standard `implementation-delivery` profile, bounded typed fields, self-hosted fixture, resolved-manifest validation, and typed-field Command support. | Core scheduling, Actual separation, standard Command families, diagnostics. | Vocabulary/state/evidence fixtures pass. This is a provisional grammar gate; M1 closes reproducible package resolution. |
| M1 — Reproducible workspace and delivery-profile completion | A user can evaluate one named immutable local Project revision and its pinned delivery package rather than an ambiguous working file. | Revision Store interface, local snapshot adapter, loader integration, and store-bound package resolution. | Resource-reference shape, snapshot identity, content identity. | Repeated Project/package evaluation is identical; Draft and stale/mismatched references fail; M0.5's pinned package-resolution acceptance is complete. |
| M2 — Reviewable projection | A user can select a View/Theme/Actual set and obtain a deterministic, traceable SVG projection. | Evaluation manifest, closure resolver, Scene builder, SVG adapter. | Core, Store, Render Context, Scene identities, diagnostics. | Plan/Actual, target capability, local/global SceneDelta fixtures pass. |
| M3 — Controlled change | A user or host can make a semantic change safely and obtain a new immutable revision. | Command executor, transactional local write, undo/redo identity, batch result. | Command envelope, CAS semantics, evaluation invalidation. | Stale revision and partial batch reject atomically; accepted change re-evaluates through the same closure. |
| M4 — Minimal product complete | A user can consume a pinned subproject summary without sharing or mutating its source. | Read-only Federation resolver, trust policy integration, repin flow, aggregate Scene input. | Store, closure, Command, Scene, parent/child authority boundary. | Trust, unavailable export, pin/repin, namespace, and child-mutation denial fixtures pass. |
| M5 — Automation, review, and AI proposals | A developer or AI agent can validate, render, and propose the same reviewable change through supported automation surfaces. | CLI adapter, machine-readable diagnostics/results, semantic diff/review presentation, AI Command-proposal adapter, and authorization-policy integration. | Command API, Store, validation, scheduler, SVG/Scene pipeline. | CLI and AI proposal results match library results; ambiguous intent, unauthorized action, and every Command bypass are rejected. |
| M5.5 — Observed Actual intake | A team can import externally observed Actual data into an explicit reconciliation queue without altering the plan. | Source-ingestion adapter, stable external identity, resolved/unmatched intake result, provenance diagnostics, and review handoff. | Actual-set model, Command boundary, Render Context, and immutable revision identity. | Imported observations preserve source identity; unmatched inputs remain visible; no intake result reschedules a Project or bypasses later reconciliation. |
| M6 — Interactive review | A user can inspect multiple views and Plan-versus-Actual without a full-scene replacement for a local change. | Read-only interactive adapter, SceneDelta application, accessibility surface. | Render Context, View/Style/Theme, SceneDelta, evaluation cache. | Local-change impact fixtures and accessibility acceptance tests pass in the client. |
| M7 — Interactive editing | A user can edit plans, annotations, imported-Actual reconciliation, and baselines in the interactive client. | Gesture-to-Command adapter, conflict/stale UI, undo/redo UI, annotation editor, and intake-queue reconciliation UI. | Command executor and transaction results; no direct Project or Scene mutation. | Client emits only valid Commands; conflict and rollback fixtures pass; imported Actual is reconciled only through a Command. |
| M8 — Extensible domain product | A semiconductor team can acquire and use declarative vocabulary/profile packages predictably. | FD-4 package registry/acquisition adapter, profile UX, lifecycle diagnostics, and declared compatibility closure. | The M0.5 profile/package path, Core-boundary rules, Revision Store resolution. | Package compatibility, inheritance, missing/cyclic package, and executable-content rejection diagnostics pass. |
| M9 — Current-profile product release | Users can work across project views, automation/AI proposals, Actual intake/reconciliation, interactive editing, extensions, federation, and declared current-profile outputs. | FD-5 target adapters, release packaging, end-to-end acceptance suite, and output capability/fidelity manifest. | All prior shared contracts; only output/client adapters vary. | Use-case acceptance review covers UC-01–UC-15 at the delivered-adapter level; each claimed target passes its declared capability evidence. |
| M10 — DateTime and recurrence product | A cross-zone team can plan DateTime events and recurrences without DST ambiguity while Date-only Projects remain unchanged. | FD-1 temporal-profile runtime, migration path, DateTime/DST scheduler support, and recurrence adapter. | Revision Store, Command, Scene, and Date-only Core compatibility. | UC-16 acceptance passes with cross-zone, fold/gap, recurrence, migration, and Date-only compatibility evidence. |
| M11 — Capacity and accounting product | A planner can evaluate capacity, accept an explicit leveling proposal, and review cost/time observations without automatic rescheduling. | FD-2 capacity evaluator, proposal/Command path, accounting observation adapter, and comparison surface. | Project/Actual authority split, Store, Command, and Scene contracts. | UC-17 and UC-18 acceptance passes with deterministic objective, stale-proposal, unit, overload, and schedule-isolation evidence. |
| M12 — Collaborative workspace product | Teams can synchronize, resolve conflicts, approve changes, and audit provenance without last-writer-wins. | FD-3 synchronization service, typed conflict/merge flow, policy/approval adapter, and append-only audit surface. | Revision Store snapshots, Command, Federation pinning, and Scene non-authority. | UC-19–UC-21 acceptance passes with conflict, approval, denial, expiry, offline, and causally-behind replica evidence. |
| M13 — Successor-capability product release | Users can combine approved DateTime, capacity/accounting, collaboration, extension lifecycle, and output capabilities in declared profiles. | Cross-successor compatibility suite, migration/release packaging, and UC-16–UC-21 acceptance review. | All current-profile and successor contracts; each capability remains opt-in and versioned. | Release review names every claimed successor profile and passes its dedicated plus cross-profile evidence without changing Date-only meaning. |
| M14 — Review SVG expression | A reviewer can distinguish plan, Actual, known variance, dependencies, and annotations in a deterministic accessible SVG. | Explicit Review SVG profile, View/Style/Theme projection, Review Scene, and SVG adapter. | Existing Project/Schedule/Actual/View/Style/Theme/Scene/Output contracts. | Controller review sample demonstrates Plan/Actual/missing/unmatched states; output is deterministic and capability-complete. |
| M15 — Table-timeline review surface | A reviewer can use a semantic table, hierarchical calendar, and user-selected group presentation in one deterministic review SVG. | Closed View table columns; table-timeline profile; axis/group/routing Scene contract; light executive sample. | Project/Schedule/Actual truth, View selection/window/grouping, and M14 comparison semantics. | Design gates D15-1–D15-3 close and I15 passes deterministic, accessibility, conformance, and reuse review evidence. |
| M16 — Decision and risk surfaces | A reviewer can add bounded, source-traceable summary panels without fabricated health or forecast values. | Read-only metric catalog; summary profile; panel Scene contract; dark delivery-control sample. | M15 projection facts, Project/Schedule/Actual authority, Output capability rules. | D16-1–D16-2 close and I16 proves metric provenance, unavailable-data diagnostics, and deterministic output. |
| M17 — Presentation themes and expression | A user can apply accessible light executive and dark delivery-control themes to the same review semantics. | Role/token catalog, contrast rules, gallery/visual-regression policy, theme samples. | M15/M16 profiles and shared semantic closure. | D17-1–D17-2 close and I17 passes cross-theme semantic, accessibility, and deterministic-output evidence. |
| M18 — Product presentation release | Users can rely on presentation compositions as one product surface rather than isolated SVG samples. | Cross-profile acceptance, capability/release manifest, and reuse review. | All M0–M17 shared contracts. | Full inherited conformance, declared output capability, accessibility, and no-parallel-model reuse evidence. |
| M19 — Layout grammar | Designers can declare reusable composition constraints without creating a second semantic model. | Layout Profile schema, migration from M15 profile, validation, fixtures, and ADR. | View/Style/Theme/Render Context/Scene ownership. | Invalid overlaps and unavailable slots diagnose; two profiles validate over one View. |
| M20 — Constraint layout runtime | A profile resolves deterministic regions, slots, and a reviewable Layout Manifest. | Solver, manifest, capability/overflow diagnostics, and SVG adapter migration. | M19 grammar and all semantic projection inputs. | Repeated output/manifest equality and no profile-ID branches. |
| M21 — Expressive review primitives | Designers can compose calendar, table, group, milestone, callout, and connector hierarchy. | Role/slot primitives, bounded formatter catalog, and acceptance gallery. | M20 solver, Style roles, Theme tokens. | Light executive acceptance with source/accessibility evidence. |
| M22 — Designer workflow release | Human and AI designers share one validated preset/proposal and release path. | Inheritance, proposal validation, accessibility/gallery, cross-profile release review. | M19–M21 resource closure. | Identical validation path, conformance, and reuse release evidence. |
| M23 — Reference-quality review detail | Reviewers can combine the Gantt with source-traceable group explanations, observations, and milestone digest content. | Review Detail Profile schema/resolver, Layout sources, completed Scene/SVG primitives, and Controller Z acceptance resources. | Project/Schedule/Actual authority, View selection/group order, v0.2 Settings/Preset resolution, shared Layout/Scene/SVG path. | Schema and semantic negatives, required overflow, source metadata, byte-identical reproduction, raster/visual acceptance, inherited conformance, and final reuse review pass. |
| M24 — Intent-oriented layout authoring | Designers can compose common document and visualization layouts without calculating coordinates or routinely entering raw distances. | Replacement Layout Profile grammar, spacing tokens/templates, intrinsic sizing, two-axis alignment/distribution, bounded anchors/guides/barriers, deterministic solver/manifest, obsolete-path removal and authoring examples. | View/Style/Theme/Layout/Scene authority and measured text; no legacy layout path is retained. | Design gates L24-D1–L24-D3 publish before implementation; centered/relative/barrier layouts reflow deterministically, stable-ID overrides avoid array replacement, invalid constraints diagnose, retained semantic conformance remains green, and superseded layout contracts are absent. |
| M25 — Color Scheme authoring | A non-designer can compare coherent, accessible named color alternatives without editing Theme values or changing semantic meaning. | Versioned Color Scheme resource, Theme intent bindings, deterministic categorical assignment, accessibility validation, and preview/gallery integration. | Style role resolution, Theme typography/metrics/markers, Layout, Context, Scene, and output capability contracts. | Design gates C25-D1–C25-D3 publish before implementation; switching a scheme changes only resolved color values, semantic/non-color cues remain intact, categorical assignment is repeatable, and no renderer palette default exists. |
| M26 — Operational review workflows | A team can intake external Actuals, capture/compare named baselines, and run the same revision-bound operations from CI. | Intake request/report, reconciliation Commands, immutable Snapshot capture/compare, automation envelope, CLI/CI adapters, and acceptance evidence. | Project/Actual/Snapshot/Command/Revision Store/Render Context authority. | Complete: C26-D1–D4, I26-1–I26-7, A26-01–A26-10 and operational conformance pass; no title matching, mutable tip, direct source-file write, scheduler mutation, or renderer fallback is reachable. |
| M27 — Presentation product-path recovery | Review output restores the declared, source-traceable presentation vocabulary through one declarative Context→Scene→SVG path. | Complete Scene composition, policy resolution, artifact materializer, reproduction conformance, and regression acceptance. | View/Detail/Theme/Color Scheme/Layout/Scene/SVG ownership; Project/Schedule/Actual semantics remain unchanged. | D27-1–D27-5 complete before implementation; no source-ID branch, renderer-local display policy, old layout grammar, or parallel serializer fallback. |

## 4. Boundaries after M24

M14 is the completed review-SVG foundation. M15–M18 are completed prototype/product
work; M19–M22 replace overlapping composition authority with a Layout Profile before
further presentation implementation. M23 completes the bounded review-detail panels
without adding scheduling, Actual, or summary-metric authority. M24 introduces the
intent-oriented authoring replacement governed by
`declarative-layout-language-plan-2026-09-20.md`. Because no external user compatibility
exists, M24 removes the prototype grammar and duplicate layout authority instead of
preserving a parallel legacy path. Ticket/workflow management,
automatic transitions, arbitrary extension code,
undisclosed output degradation, raster/PDF claims, and any successor capability not
named by this roadmap require a new owning-specification change and roadmap amendment.
They are not hidden work inside a milestone above.

M25 is complete. Color Scheme extends Theme resolution but does not replace Theme,
Style, Layout, or Scene ownership. A successor color-scale, automatic host-mode, or
renderer-local palette feature requires a new owning specification and milestone.

M26 is complete as an operational adapter milestone. It does not redefine Project,
Actual, Snapshot, Command, or Revision Store semantics; the CLI only consumes declared
immutable references and the configured local Store routing.

M27 repairs the presentation product path exposed by Issues #29–#33. It is design-only
until D27-1–D27-5 close and may not turn old example output into an undeclared
compatibility contract.

Issues 1–10 are governed by
`issue-remediation-program-2026-09-20.md`. That program reopens acceptance evidence for
M0, M1, M5, and M22 before any deferred M23 implementation; it is not a new feature
milestone and does not authorize the deferred M23 panel families.

## 4.1 Future-capability design gate

`future-capability-design-completion-plan.md` governs FD-1–FD-5. FD-4 and FD-5 are
implemented by M8 and M9; FD-1, FD-2, and FD-3 are implemented by M10, M11, and M12.
This gate exists to expose compatibility and migration consequences before
implementation, not to let a later adapter redefine Core semantics.

## 5. Milestone reviews

At the end of M2, M4, M7, M9, M10, M11, M12, and M13, conduct a reuse review in addition to feature tests.
It must show that the shared Core/Store/Command/Scene contracts remain the execution
path, list any adapter intentionally replaced, and reject any duplicated semantic
model. This is the control that prevents the minimal implementation from becoming
throwaway code.
