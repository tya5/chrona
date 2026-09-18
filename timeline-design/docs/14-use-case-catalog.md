# Use Case Catalog

**Status:** Draft
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

## 5. Cross-cutting quality scenarios

| ID | Scenario | Acceptance criterion |
|---|---|---|
| Q-UC-01 | Re-evaluate the same immutable inputs | Same schedule, projection, Scene, and diagnostics |
| Q-UC-02 | Change one Actual observation | Only comparison-dependent Scene nodes change; no unexplained whole-Scene replacement |
| Q-UC-03 | Change viewport or scale | Global `replaceScope` is allowed and carries its declared reason |
| Q-UC-04 | Compare named revisions | Inputs include immutable Project/Snapshot identities; no current branch or local clock |
| Q-UC-05 | Render inaccessible target | Missing required capability is diagnosed, not silently approximated |

## 6. Specification and evidence mapping

| Use case | Primary specifications | Current evidence | Remaining gap |
|---|---|---|---|
| UC-01 | `02`–`05`, `12` | Core schemas and scheduling fixtures | integrated CI validation |
| UC-02 | `05`, `09`, `10`, `13` | normalized format and Command contract | semantic Git-diff presentation |
| UC-03 | `06`, `07`, `10`, `12`, `13` | Actual/View/Style fixtures | semantic runner and rendered comparison |
| UC-04 | `06`–`09`, `12`, `13` | Render Context and Theme fixtures | exporter adapter |
| UC-05 | `08`–`10`, `12`, `13` | Command and SceneDelta fixtures | interactive editor adapter/delta computation |
| UC-06 | `09`–`12` | request schema and reject fixture | AI adapter and authorization policy |
| UC-07 | `02`, `04`, `05`, `11`, `12` | extension model prose | package schema and fixtures |
| UC-08 | `06`, `08`, `10`, `12` | annotation intent fixture | annotation command and editor adapter |
| UC-09 | `05`–`09`, `13` | named multi-context fixture | isolation runner and adapters |
| UC-10 | `06`, `10`, `12`, `13` | resolved/unmatched and resolution-command fixtures | ingestion adapter |
| UC-11 | `05`, `09`, `10`, `12`, `13` | conformance manifest | runner, CLI, CI integration |
| UC-12 | `05`, `06`, `10`, `12`, `13` | Snapshot reference and capture-command fixtures | comparison runner |
| UC-13 | `07`–`09`, `12`, `13` | target capability contract | SVG/PPTX/canvas adapters |

## 7. Current gaps and release gate

The specifications cover the intended meaning and structural fixtures for UC-01 through
UC-06. The following evidence is still required before claiming executable support:

1. schema validator and semantic conformance runner;
2. SceneDelta computation and invariants for Q-UC-02/Q-UC-03;
3. renderer/exporter implementation for UC-04;
4. interactive editor adapter for UC-05;
5. AI adapter and authorization policy for UC-06; and
6. extension package schema and fixtures for UC-07.

A release claim must name the satisfied use cases and their acceptance evidence rather
than describing the entire catalog as implemented.
