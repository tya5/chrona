# Use Case Catalog

**Status:** Proposed
**Depends on:** [00 Vision](00-vision.md), [02 Domain Model](02-domain-model.md), [04 Scheduling Model](04-scheduling-model.md), [06 View Model](06-view-model.md), [09 Application Architecture](09-application-architecture.md), [10 Command Model](10-command-model.md), [12 Quality and Invariants](12-quality-and-invariants.md)  
**Owns:** representative user goals, acceptance criteria, design-coverage analysis, and explicit use-case gaps.

## 1. Purpose

This catalog turns the representative use cases in the Vision into reviewable scenarios.
It answers whether Chrona's specifications can support an intended user outcome—not
whether a particular GUI or renderer has already been implemented.

It does not redefine the semantics owned by Core, Presentation, or Command documents.
Every rule referenced below remains owned by the linked specification.

## 2. Actors and evidence

| Actor | Goal | Primary evidence |
|---|---|---|
| Engineering planner | Maintain an explainable development plan | Project files, scheduling diagnostics |
| Engineering reviewer | Understand a proposed schedule change | Git diff, View, comparison projection |
| Program / customer reviewer | Understand plan, Actual, and key dates | Render Context, View, Scene artifact |
| Interactive editor user | Propose a valid semantic change | Command result and SceneDelta |
| AI agent | Request a reviewable, safe change | Typed Command and diagnostics |

Each use case records: trigger, preconditions, outcome, exceptional behavior,
acceptance evidence, and owning specifications. A use case is satisfied only when its
acceptance evidence can be reproduced from explicit inputs.

## 3. Summary and priority

| ID | Use case | Priority | Current coverage |
|---|---|---|---|
| UC-01 | Create and validate an engineering development timeline | Must | Core v0.1 design and fixtures |
| UC-02 | Review a schedule change in Git | Must | Core semantics and normalized files; rendered review deferred |
| UC-03 | Review plan versus Actual | Must | View/Actual/Style design and structural fixtures |
| UC-04 | Produce a customer-facing projection | Should | View/Style/Theme/Scene design; exporter deferred |
| UC-05 | Edit a plan interactively without global UI replacement | Must | Command/SceneDelta contract and fixtures; editor deferred |
| UC-06 | Request a safe AI-assisted edit | Should | Command model and request fixtures; agent adapter deferred |
| UC-07 | Model semiconductor gates and domain vocabulary | Should | Profile/extension design; package fixtures deferred |
| UC-08 | Add expressive explanatory annotations without changing schedule semantics | Must | Presentation-annotation design; editor evidence deferred |
| UC-09 | Maintain multiple purpose-specific views from one Project | Must | View/Style/Theme/Render Context design and fixtures |
| UC-10 | Import and reconcile externally observed Actual data | Should | Actual-set design and unmatched fixture; ingestion adapter deferred |
| UC-11 | Validate, render, and propose changes through CLI/automation | Should | Command/conformance design; adapter and CI deferred |
| UC-12 | Capture and compare a named baseline | Should | Snapshot-reference design; capture command deferred |
| UC-13 | Export one evaluation to declared targets | Should | Scene/target capability design; SVG/PPTX adapters deferred |
| UC-14 | Federate independently owned subproject timelines | Must | Pinned federation contract and conformance evidence; resolver/aggregate adapter required |
| UC-15 | Manage a delivery roadmap using Chrona | Must | Delivery-profile plan; profile/fixture implementation required |
| UC-16 | Plan a cross-zone event without DST ambiguity | Future | DateTime/DST successor design and fixtures; runtime deferred |
| UC-17 | Assess capacity and accept an explicit leveling proposal | Future | Resource/capacity successor design and fixtures; solver deferred |
| UC-18 | Record cost and time observations without rescheduling the plan | Future | Cost/time observation boundary and fixtures; adapter deferred |
| UC-19 | Resolve a concurrent semantic conflict explicitly | Future | Collaboration merge design and fixtures; service deferred |
| UC-20 | Approve and audit a controlled change | Future | Authorization/approval/audit design and fixtures; policy integration deferred |
| UC-21 | Synchronize a replica without treating a remote tip as truth | Future | Hosted-sync design and fixtures; service deferred |

## 4. Detailed use cases

### UC-01 — Create and validate an engineering development timeline

**Trigger:** A planner records milestones, spans, dependencies, calendars, and
constraints for a development program.

**Preconditions:** The Project uses declared Core profiles and Date-only v0.1 values.

**Outcome:** Chrona normalizes the Project, derives a deterministic planned schedule,
and reports invalid dependencies, dates, calendars, or constraints as diagnostics.

**Acceptance evidence:** Core schema, canonical scheduling fixtures, and deterministic
schedule output for the same Project revision.

**Exceptional behavior:** Invalid input is diagnosed; derived placement is never
silently written as fixed Project data.

**Owners:** `02`–`05`, `12`.

### UC-02 — Review a schedule change in Git

**Trigger:** A reviewer opens a proposed Project revision.

**Outcome:** The reviewer can identify the changed semantic fields, their scheduling
effect, and resulting diagnostics without interpreting SVG or canvas coordinates.

**Acceptance evidence:** Normalized Git diff, revision-bound evaluation manifest, and
stable IDs in command/result diagnostics.

**Exceptional behavior:** A moving branch, implicit working-tree tip, or renderer
default is not accepted as a reproducible comparison input.

**Owners:** `05`, `09`, `10`, `13`.

### UC-03 — Review plan versus Actual

**Trigger:** A reviewer selects a View that requires Actual observations.

**Outcome:** Planned placement and independently observed Actual are shown as distinct
comparison facets. Start/finish variance, progress, missing Actual, and unmatched Actual
remain explicit; no Actual automatically changes the planned schedule.

**Acceptance evidence:** Render Context, Actual-set fixture, View facets, Style roles,
and diagnostics for missing or unmatched alignment.

**Exceptional behavior:** Unknown object IDs are diagnosed and never title-matched.

**Owners:** `06`, `07`, `10`, `12`, `13`.

### UC-04 — Produce a customer-facing projection

**Trigger:** A program reviewer requests a named customer-facing Render Context.

**Outcome:** A View selects an approved subset and a Theme changes appearance without
changing Project facts, scheduling, or comparison identity.

**Acceptance evidence:** Explicit Render Context, named View/Style/Theme/Scene profile,
and reproducible Scene input manifest.

**Exceptional behavior:** Missing capability or unresolved token yields a diagnostic;
the renderer does not choose a local fallback.

**Owners:** `06`–`09`, `12`, `13`.

### UC-05 — Edit a plan interactively without global UI replacement

**Trigger:** A user drags or edits one temporal object, annotation, or Actual
observation in an editor.

**Outcome:** The client submits a revision-bound semantic Command. On acceptance, it
receives a SceneDelta whose operations update only the affected Scene nodes unless the
declared impact domain is genuinely global.

**Acceptance evidence:** accepted/rejected Command fixture; local Actual SceneDelta
fixture; global viewport-reflow fixture; invariant test that unexplained `replaceScope`
fails.

**Exceptional behavior:** Stale commands are rejected; preview state is removed or
corrected without directly editing canonical or Scene state.

**Owners:** `08`–`10`, `12`, `13`.

### UC-06 — Request a safe AI-assisted edit

**Trigger:** An AI agent proposes an edit from natural-language intent.

**Outcome:** The agent submits the same typed Command and base revision as a GUI or CLI.
The resulting semantic change, diagnostics, and new revision are reviewable.

**Acceptance evidence:** Command request schema, accept/reject fixtures, and command
result contract.

**Exceptional behavior:** Ambiguous title matching, arbitrary source rewrite, and
host-language execution are rejected.

**Owners:** `09`, `10`, `11`, `12`.

### UC-07 — Model semiconductor gates and domain vocabulary

**Trigger:** A team models gates such as EVT, DVT, PVT, qualification, component, or
customer review.

**Outcome:** The vocabulary is represented by declared profiles and typed fields while
retaining Core Point/Span, relation, and scheduling semantics.

**Acceptance evidence:** Extension package schema, deterministic normalization, and
fixtures that retain stable identity and validation behavior.

**Exceptional behavior:** The extension cannot introduce executable rules, resource
leveling, cost, ticket workflow, or a new scheduling primitive without Core review.

**Owners:** `02`, `04`, `05`, `11`, `12`.

### UC-08 — Add expressive explanatory annotations without changing schedule semantics

**Trigger:** A reviewer adds a callout, highlight, note, or explanatory arrow to make a
timeline understandable in an engineering, executive, or customer review.

**Outcome:** The annotation has a stable View-local anchor and logical placement intent.
An explanatory arrow remains distinct from a semantic dependency and does not constrain
or alter scheduling.

**Acceptance evidence:** Presentation-annotation command, View-local stable anchor,
and Scene primitives carrying distinct source kinds and roles.

**Exceptional behavior:** Editing pixel offsets, an SVG path, or a canvas shape alone
does not mutate the annotation or Project. Missing anchors are diagnosed.

**Owners:** `06`, `08`, `10`, `12`.

### UC-09 — Maintain multiple purpose-specific views from one Project

**Trigger:** A team needs engineering, executive, and customer review projections of
the same semantic Project revision.

**Outcome:** Each named Render Context selects its View, Style, Theme, Scene profile,
and comparison inputs explicitly. Project facts are not copied into presentation files.

**Acceptance evidence:** Multiple Render Context fixtures bound to one immutable Project
revision, with distinct View/Theme identities and reproducible input manifests.

**Exceptional behavior:** A View cannot select a hidden current branch, default theme,
or local renderer configuration.

**Owners:** `05`–`09`, `13`.

### UC-10 — Import and reconcile externally observed Actual data

**Trigger:** An external source supplies an observation that may not yet have a Project
object identity.

**Outcome:** Chrona records it with an external identity and `alignment: unmatched`, or
records a resolved stable `projectObjectId`. A reviewer can later issue an explicit
alignment edit.

**Acceptance evidence:** Actual-set resolved/unmatched fixtures, alignment diagnostics,
and a revision-bound Command result.

**Exceptional behavior:** Title similarity never creates an alignment. An unmatched
observation remains visible and never reschedules the plan.

**Owners:** `06`, `10`, `12`, `13`.

### UC-11 — Validate, render, and propose changes through CLI/automation

**Trigger:** A Git hook, CI job, or automation workflow validates a revision, requests
a declared artifact, or submits a typed change proposal.

**Outcome:** It uses the same schemas, explicit Render Context, Command Engine, and
diagnostic contract as an interactive client.

**Acceptance evidence:** Conformance manifest/runner, revision-bound command document,
and deterministic output manifest.

**Exceptional behavior:** Automation cannot mutate a working-tree default, bypass base
revision checks, or execute arbitrary project-file code.

**Owners:** `05`, `09`, `10`, `12`, `13`.

### UC-12 — Capture and compare a named baseline

**Trigger:** A planner approves a revision as a baseline and later compares it to the
current Project and/or Actual observations.

**Outcome:** The comparison names an immutable Snapshot reference; missing or changed
objects are comparison facts, not implicit mutations.

**Acceptance evidence:** Snapshot reference fixture, immutable revision diagnostic, and
View comparison facets.

**Exceptional behavior:** A moving branch cannot be used as a reproducible baseline;
capture workflow remains unavailable until its explicit Command is specified.

**Owners:** `05`, `06`, `10`, `12`, `13`.

### UC-13 — Export one evaluation to declared targets

**Trigger:** A reviewer requests SVG now, or a future interactive/canvas/PPTX target,
from a named Render Context.

**Outcome:** The Scene is derived from the same explicit evaluation inputs. Required
target capabilities are checked before adaptation, so meaningful distinctions are not
silently lost.

**Acceptance evidence:** target-capability diagnostic, Scene input manifest, and
adapter-specific golden artifact when an adapter exists.

**Exceptional behavior:** A renderer cannot replace missing token, font metric, marker,
or accessibility capability with an unstated local default.

**Owners:** `07`–`09`, `12`, `13`.

### UC-14 — Federate independently owned subproject timelines

**Actor:** Program lead; subproject leaders.
**Trigger:** A program needs an integrated milestone/risk timeline while each team keeps
its own Project, repository, and review cadence.
**Preconditions:** Each subproject publishes an immutable Chrona timeline export; the
program repository declares only pinned references in a Federation Plan.
**Normal flow:** A subproject leader changes and reviews only their own Project. The
program lead updates one federation reference to an approved child revision, resolves
the closure, and renders child summary items alongside program-owned milestones.
**Outcome:** The parent can compare the exact child revisions it consumed without
editing, copying, or implicitly scheduling child source data.
**Exceptional flow:** Missing, untrusted, incompatible, or stale child export produces a
diagnostic and an explicit unavailable/stale summary; it never silently reads a child
branch tip.
**Acceptance:** Separate repositories/files have separate command targets and history;
the parent diff contains only a pinned reference update; the resolved federation manifest
records every child revision/content identity.

**Owners:** `05`, `06`, `09`, `12`, `13`, `16`.

### UC-15 — Manage a delivery roadmap using Chrona

**Actor:** Engineering or product lead.
**Trigger:** The team plans, reviews, or accepts Chrona delivery work and needs the
plan itself to be a reproducible Chrona Project.
**Preconditions:** The Project resolves the standard `implementation-delivery` profile
at an immutable package identity.
**Normal flow:** The lead records delivery work items and gates, their ordinary temporal
relations, typed assignee references, workflow state, immutable artifacts, acceptance
evidence, and reuse classification. Chrona validates and schedules the Project through
the ordinary Core path; a validated field change is submitted as an ordinary Command.
**Outcome:** The delivery plan is reviewable as canonical Project data and can use the
same validation, scheduling, revision, and presentation path as any other plan.
**Exceptional flow:** Unknown profile fields, unpinned or mismatched evidence, an
unsupported state, or a state that attempts to affect schedule/Actual is diagnosed;
the plan is not silently reinterpreted as a workflow engine.
**Acceptance:** Canonical fixtures show deterministic schedule equivalence across
workflow-state changes, separate Actual resolution, immutable evidence validation, and
a self-hosted Chrona delivery-plan Project.

**Owners:** `02`, `04`, `05`, `10`, `11`, `12`, `15`.

### UC-16 — Plan a cross-zone event without DST ambiguity

**Actor:** Program planner.
**Trigger:** The planner schedules a DateTime event across zones or enters a local
wall-clock time near a daylight-saving transition.
**Preconditions:** The Project explicitly selects `temporalProfile: datetime-v0.2`.
**Outcome:** Chrona stores an instant plus IANA zone, applies the declared local-time
disambiguation, and derives the same cross-zone ordering for the same immutable input.
**Exceptional behavior:** A mixed Date/DateTime dependency, an ambiguous local time
without `earlier`, `later`, or `reject`, and a nonexistent local time are rejected with
the specified diagnostics; no gap is silently shifted.
**Acceptance evidence:** v0.2 temporal schema and fixtures for cross-zone comparison,
DST folds/gaps, CalendarPeriod across DST, recurrence, and Date-only compatibility.
**Owners:** `03`, `04`, `05`, `12`, `18`.

### UC-17 — Assess capacity and accept an explicit leveling proposal

**Actor:** Resource planner.
**Trigger:** The planner evaluates a declared resource-capacity set against Project
demand and requests a permitted leveling objective.
**Preconditions:** The successor Project and capacity inputs name immutable revisions,
dimensioned units, permitted movement scope, and a deterministic objective.
**Outcome:** Chrona reports overloads and returns an explicitly derived proposal. The
Project changes only if a reviewer accepts that proposal through a current-revision
Command.
**Exceptional behavior:** Incompatible units, unavailable capacity, fixed-placement
movement, and stale proposals are diagnosed. Capacity infeasibility never silently
rewrites dates or turns an Actual observation into a scheduling input.
**Acceptance evidence:** successor schemas and fixtures for units, assignments,
capacity calendars, overloads, deterministic tie breaks, and stale-proposal rejection.
**Owners:** `02`, `04`, `05`, `10`, `12`, `19`.

### UC-18 — Record cost and time observations without rescheduling the plan

**Actor:** Delivery controller.
**Trigger:** The controller records cost, timesheet, or actual-effort observations
against planned demand.
**Preconditions:** Each observation has its own identity and revision provenance.
**Outcome:** Chrona derives auditable aggregates and may display them beside plan
demand while preserving their independence from schedule and capacity authority.
**Exceptional behavior:** Missing, mismatched, or stale observation identities are
diagnosed. Cost, timesheet, and actual effort never infer progress or reschedule a
Project automatically.
**Acceptance evidence:** cost/time observation schemas and fixtures proving identity,
aggregation provenance, and schedule isolation.
**Owners:** `05`, `06`, `12`, `19`.

### UC-19 — Resolve a concurrent semantic conflict explicitly

**Actor:** Collaborating planner.
**Trigger:** A Command based on an older immutable revision conflicts with another
accepted semantic change.
**Preconditions:** The submitted Command records its base revision and the service can
identify both immutable parent snapshots.
**Outcome:** Chrona returns a typed conflict or merge proposal with both values, paths,
and provenance. A compatible resolution becomes a new revision only through a typed
resolution Command.
**Exceptional behavior:** The service never uses last-writer-wins, infers user intent,
or merges derived schedule/Scene/output state. A stale command remains rejected until
explicitly resolved.
**Acceptance evidence:** stale-write, structural/semantic conflict, explicit
resolution, and merged-parent-provenance fixtures.
**Owners:** `09`, `10`, `12`, `15`, `20`.

### UC-20 — Approve and audit a controlled change

**Actor:** Authorized reviewer.
**Trigger:** A policy requires authorization or approval before a Command can persist.
**Preconditions:** The policy decision identifies actor, principal, action, target,
base revision, policy version, and trusted time source.
**Outcome:** An approval binds one exact Command fingerprint and the resulting audit
record explains the accepted or denied persistence decision without changing semantic
meaning.
**Exceptional behavior:** A changed payload or base revision invalidates approval;
denied or expired decisions cannot be replayed as a semantic bypass.
**Acceptance evidence:** approved, denied, expired, and fingerprint-mismatch command
fixtures plus append-only audit provenance.
**Owners:** `09`, `10`, `12`, `15`, `20`.

### UC-21 — Synchronize a replica without treating a remote tip as truth

**Actor:** Offline or hosted-workspace user.
**Trigger:** A replica exchanges immutable snapshots and pending Commands with a
hosted synchronization service.
**Preconditions:** The replica labels its known revision and every transferred object
has Store-issued revision/content identity.
**Outcome:** Chrona transfers snapshots, command results, conflict objects, and audit
provenance while preserving the explicit revision consumed by each evaluation.
**Exceptional behavior:** A behind replica cannot claim an unobserved tip; offline
Commands retain their original base revision; ephemeral presence/cursor state never
becomes Project data.
**Acceptance evidence:** causally-behind replica, offline stale-command, and
provenance-preserving synchronization fixtures.
**Owners:** `09`, `12`, `15`, `20`.

## 5. Cross-cutting quality scenarios

| ID | Scenario | Acceptance criterion |
|---|---|---|
| Q-UC-01 | Re-evaluate the same immutable inputs | Same schedule, projection, Scene, and diagnostics |
| Q-UC-02 | Change one Actual observation | Only comparison-dependent Scene nodes change; no unexplained whole-Scene replacement |
| Q-UC-03 | Change viewport or scale | Global `replaceScope` is allowed and carries its declared reason |
| Q-UC-04 | Compare named revisions | Inputs include immutable Project/Snapshot identities; no current branch or local clock |
| Q-UC-05 | Render inaccessible target | Missing required capability is diagnosed, not silently approximated |
| Q-UC-06 | Update a child Project outside the parent | Parent revision and rendered child summary remain unchanged until its pinned export reference is explicitly updated |

## 6. Specification and evidence mapping

| Use case | Primary specifications | Current evidence | Remaining gap |
|---|---|---|---|
| UC-01 | `02`–`05`, `12` | Core schemas, Calendar/WorkPeriod, dependency, and scheduling fixtures | product adapters only |
| UC-02 | `05`, `09`, `10`, `13` | normalized format, Command envelope, and revision-store fixtures | semantic Git-diff presentation adapter |
| UC-03 | `06`, `07`, `10`, `12`, `13` | Actual/View/Style, SceneDelta, and comparison fixtures | interactive/renderer adapters |
| UC-04 | `06`–`09`, `12`, `13` | Render Context, Theme, closure, and output-manifest contracts | additional exporter adapters |
| UC-05 | `08`–`10`, `12`, `13` | Command, SceneDelta, and gesture-boundary fixtures | interactive editor adapter |
| UC-06 | `09`–`12` | request schema, reject fixture, and Command authorization boundary | AI adapter/policy integration |
| UC-07 | `02`, `04`, `05`, `11`, `12` | extension package reference schema, lifecycle fixture, and diagnostics | package registry UX |
| UC-08 | `06`, `08`, `10`, `12` | annotation intent, command, anchor, and Scene-role contracts | annotation editor adapter |
| UC-09 | `05`–`09`, `13` | named multi-context fixture, isolation rule, and reproducible closure | view/client adapters |
| UC-10 | `06`, `10`, `12`, `13` | resolved/unmatched Actual and resolution-command fixtures | ingestion adapter |
| UC-11 | `05`, `09`, `10`, `12`, `13` | conformance manifest, runner contract, and revision-bound Command document | CLI/CI integration |
| UC-12 | `05`, `06`, `10`, `12`, `13` | Snapshot reference and capture-command fixtures | comparison adapter |
| UC-13 | `07`–`09`, `12`, `13`, `22` | output-capability schema, fidelity diagnostics, and target fixture | non-SVG target adapters |
| UC-14 | `05`, `06`, `09`, `12`, `13`, `15`, `16` | pinned Git/local/content closure, trust/repin diagnostics, and aggregate-projection fixture | resolver and aggregate Scene adapter |
| UC-15 | `02`, `04`, `05`, `10`, `11`, `12`, `15`, `17` | delivery profile schema, vocabulary/evidence/state fixtures, roadmap fixture, and IDP-6 review | profile UX only |
| UC-16 | `03`, `04`, `05`, `12`, `18` | DateTime/DST schema, fixtures, ADR-0014, and FD-1 review | M10 runtime and migration adapter |
| UC-17 | `02`, `04`, `05`, `10`, `12`, `19` | capacity schema/fixtures, ADR-0015, and FD-2 review | M11 evaluator and proposal adapter |
| UC-18 | `05`, `06`, `12`, `19` | observation-isolation contract and capacity/cost fixtures | M11 accounting observation adapter |
| UC-19 | `09`, `10`, `12`, `15`, `20` | collaboration schema/fixtures, ADR-0016, and FD-3 review | M12 conflict/merge service |
| UC-20 | `09`, `10`, `12`, `15`, `20` | approval/denial fixture and audit-provenance contract | M12 policy and audit adapter |
| UC-21 | `09`, `12`, `15`, `20` | causally-behind replica fixture and sync provenance contract | M12 hosted synchronization service |

## 7. Current gaps and release gate

Every UC-01–UC-21 row has one current normative owner, canonical positive/negative
evidence where the rule is machine-checkable, an implementation-independent acceptance
contract, and a named delivery milestone. UC-14 remains design-ready through the
pinned Git/local/content reference contract; UC-15 prevents delivery work from
inventing a parallel project-management model; UC-16–UC-21 are opt-in successor
capabilities rather than implicit changes to the Date-only profile.

The remaining gaps in this table are planned adapters or product features, not
unresolved design semantics. A release claim must name the satisfied use cases and
their acceptance evidence rather than describing the entire catalog as implemented.

## 8. Output-release successor acceptance

The future output release gate maps UC-01–UC-21 to each claimed target. At minimum,
the target manifest must show deterministic output (UC-01), source/role provenance
(UC-04/UC-09), no renderer-authoritative mutation (UC-05/UC-06), fidelity diagnostics
(UC-13), and the exact pinned closure for federation/extension cases (UC-14/UC-15).
An adapter may claim only the rows whose capability fixtures and acceptance evidence it
passes; SVG baseline success does not imply PDF, raster, canvas, or presentation
support. M13 separately reviews successor profiles and does not retroactively broaden
an M9 current-profile claim.
