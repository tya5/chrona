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

## 5. Cross-cutting quality scenarios

| ID | Scenario | Acceptance criterion |
|---|---|---|
| Q-UC-01 | Re-evaluate the same immutable inputs | Same schedule, projection, Scene, and diagnostics |
| Q-UC-02 | Change one Actual observation | Only comparison-dependent Scene nodes change; no unexplained whole-Scene replacement |
| Q-UC-03 | Change viewport or scale | Global `replaceScope` is allowed and carries its declared reason |
| Q-UC-04 | Compare named revisions | Inputs include immutable Project/Snapshot identities; no current branch or local clock |
| Q-UC-05 | Render inaccessible target | Missing required capability is diagnosed, not silently approximated |

## 6. Current gaps and release gate

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
