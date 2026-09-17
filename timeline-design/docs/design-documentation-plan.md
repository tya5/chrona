# Design Documentation Plan

**Status:** Draft  
**Version:** 0.1  
**Purpose:** Define the structure, ownership, relationships, and maintenance rules for the project's design artifacts before detailed design work begins.

## 1. Purpose

This document defines how design knowledge for the project is organized and maintained.

The project is intended to provide a Git-friendly, structured, extensible system for representing and visualizing project timelines while retaining the expressive presentation capabilities commonly achieved with slide tools. Its design spans several distinct concerns: domain semantics, temporal semantics, scheduling, serialization, presentation, rendering, application architecture, commands, and extensibility.

The purpose of this plan is to prevent those concerns from becoming mixed across documents and implementations.

This document is therefore a **meta-specification for the design documentation itself**. Subsequent design artifacts SHOULD follow the ownership and dependency rules defined here.

## 2. Documentation Principles

### 2.1 Docs as Code

Design artifacts SHOULD be stored as text files in the repository and reviewed through the same Git workflow as source code.

Markdown is the default format for human-readable specifications. YAML or another appropriate machine-readable format MAY be used for schemas, fixtures, examples, and other executable artifacts.

### 2.2 One authoritative home for each concept

Every normative design concept SHOULD have one authoritative document.

Other documents MAY summarize or reference that concept, but SHOULD NOT redefine it independently.

For example:

- temporal arithmetic belongs to the Temporal Model;
- dependency semantics belong to the Scheduling Model;
- YAML representation belongs to the Project Format;
- rendering coordinates belong to the Scene and Rendering specification.

This rule exists to prevent semantic drift.

### 2.3 Separate meaning from representation and implementation

The documentation SHALL distinguish:

1. what a concept means;
2. how that concept is serialized;
3. how it is presented;
4. how it is implemented.

In particular:

```text
Domain semantics
      ↓
Serialization
      ↓
Presentation
      ↓
Scene
      ↓
Renderer / implementation
```

A rendering technology such as tldraw MUST NOT define project semantics.

Likewise, a YAML convenience syntax MUST NOT become the definition of the domain model.

### 2.4 Specifications describe the current design; ADRs explain decisions

Normative design documents describe the design that currently applies.

Architecture Decision Records (ADRs) record significant decisions, alternatives, trade-offs, and rationale.

A reader SHOULD be able to understand the current system without reconstructing it from ADR history.

### 2.5 Examples are part of the specification

Examples are not merely tutorial material.

Canonical examples SHOULD be maintained alongside specifications and SHOULD be suitable for use as parser, validator, scheduler, renderer, and compatibility fixtures where practical.

### 2.6 Machine-readable constraints accompany prose semantics

Where a rule can be represented mechanically, schemas and validation rules SHOULD accompany the prose specification.

The prose specification remains authoritative for semantic meaning. Machine-readable schemas are authoritative for the structural constraints they explicitly encode.

### 2.7 Prefer explicit invariants

Important architectural boundaries SHOULD be expressed as explicit invariants rather than being left implicit in implementation structure.

Examples include:

- View MUST NOT alter scheduling semantics.
- Scene coordinates MUST NOT be the source of truth for temporal placement.
- Rendering MUST be reproducible from explicit inputs.
- Unknown profiles SHOULD degrade through their declared inheritance chain.

## 3. Documentation Architecture

The documentation is divided into the following logical areas.

```text
Vision / Scope
      │
      ▼
Concepts
      │
      ▼
Core Specification
 ┌───────────────┐
 │ Domain Model  │
 │ Temporal Model│
 │ Scheduling    │
 │ Project Format│
 └───────────────┘
      │
      ▼
Presentation Specification
 ┌───────────────┐
 │ View Model    │
 │ Style / Theme │
 │ Scene/Render  │
 └───────────────┘
      │
      ▼
Application Architecture
 ┌───────────────┐
 │ Components    │
 │ Commands      │
 │ Runtime       │
 └───────────────┘

Cross-cutting:
- Extension Model
- Quality and Invariants
- ADRs
- Schemas
- Examples
```

The **Core Specification** defines semantics independently of a particular editor or renderer.

The **Presentation Specification** defines how semantic project information becomes a visual projection.

The **Application Architecture** defines how an implementation realizes those specifications.

## 4. Repository Structure

The initial target structure is:

```text
docs/
├── design-documentation-plan.md
├── 00-vision.md
├── 01-concepts.md
├── 02-domain-model.md
├── 03-temporal-model.md
├── 04-scheduling-model.md
├── 05-project-format.md
├── 06-view-model.md
├── 07-style-and-theme.md
├── 08-scene-and-rendering.md
├── 09-application-architecture.md
├── 10-command-model.md
├── 11-extension-model.md
├── 12-quality-and-invariants.md
├── 13-presentation-format.md
│
├── decisions/
│   └── ADR-NNNN-<decision>.md
│
├── schemas/
│   └── ...
│
└── examples/
    └── ...
```

This is a logical structure, not a commitment that every document must remain a single file. A document MAY later become a directory when its scope justifies subdivision, provided its ownership boundary remains unchanged.

## 5. Artifact Catalog

### 5.1 `design-documentation-plan.md`

**Purpose**

Defines the documentation architecture and governance rules.

**Owns**

- artifact taxonomy;
- document responsibilities;
- source-of-truth rules;
- dependency rules;
- maturity states;
- change process;
- initial design roadmap.

**Does not own**

Any project-domain or implementation semantics.

---

### 5.2 `00-vision.md`

**Purpose**

Defines what the product is intended to accomplish and where its scope ends.

**Owns**

- problem statement;
- goals;
- non-goals;
- target use cases;
- product principles;
- major quality goals;
- positioning.

**Does not own**

Detailed domain types, serialization, scheduling algorithms, or UI architecture.

---

### 5.3 `01-concepts.md`

**Purpose**

Provides the common vocabulary and conceptual map required to read the remaining specifications.

**Owns**

Definitions and relationships for major concepts such as:

- Project;
- Temporal Object;
- Point;
- Span;
- Entity;
- Relation;
- Annotation;
- Profile;
- Schedule;
- Calendar;
- View;
- Style;
- Theme;
- Scene;
- Snapshot.

**Does not own**

Detailed field definitions or algorithms.

---

### 5.4 `02-domain-model.md`

**Purpose**

Defines the semantic objects that may exist in a project independently of serialization and presentation.

**Owns**

- semantic core primitives;
- TemporalPoint and TemporalSpan as domain objects;
- Entity;
- Relation;
- Annotation;
- identity and references;
- profile/type specialization;
- common semantic fields;
- relationships between core objects.

**Does not own**

- temporal arithmetic;
- scheduling rules;
- YAML syntax;
- visual geometry;
- renderer-specific objects.

**Depends on**

`01-concepts.md`

---

### 5.5 `03-temporal-model.md`

**Purpose**

Defines the pure model of time used throughout the system.

**Owns**

- Date and DateTime;
- temporal coordinate domains;
- ExactDuration;
- CalendarPeriod;
- WorkPeriod;
- Calendar;
- precision;
- uncertainty;
- interval semantics;
- half-open intervals `[start, end)`;
- temporal arithmetic;
- `advance`, `retreat`, and difference operations;
- rules for calendar and timezone context.

**Does not own**

- Task or Milestone semantics;
- dependency semantics;
- scheduling policies;
- YAML representation;
- rendering.

**Depends on**

`01-concepts.md`

---

### 5.6 `04-scheduling-model.md`

**Purpose**

Defines how temporal placements are determined and constrained.

**Owns**

- fixed, derived, and scheduled placement;
- schedule authority;
- anchors;
- endpoints;
- lower and upper temporal bounds;
- constraints;
- dependencies;
- lag semantics;
- deadline semantics;
- calendar validity during scheduling;
- dependency endpoint mapping;
- scheduling conflicts and invalid states;
- normative scheduling behavior.

The dependency model SHOULD reduce to the general form:

```text
target.endpoint >= advance(source.endpoint, lag)
```

Traditional FS/SS/FF/SF terminology is treated as a compatibility vocabulary over endpoint pairs rather than as separate primitives.

**Does not own**

- temporal arithmetic itself;
- YAML syntax;
- rendering;
- implementation-specific scheduler algorithms unless required to guarantee observable semantics.

**Depends on**

`02-domain-model.md`, `03-temporal-model.md`

---

### 5.7 `05-project-format.md`

**Purpose**

Defines the persistent, Git-friendly project representation.

**Owns**

- document/file structure;
- YAML syntax;
- canonical representation;
- shorthand syntax;
- normalization;
- stable identifiers;
- references;
- default values;
- ordering rules;
- versioning;
- unknown-field behavior;
- migration;
- multi-file composition;
- serialization of domain, temporal, and scheduling concepts.

**Does not own**

The semantic meaning of concepts defined by the Core Specification.

**Depends on**

`02-domain-model.md`, `03-temporal-model.md`, `04-scheduling-model.md`

---

### 5.8 `06-view-model.md`

**Purpose**

Defines how a project is selected, grouped, ordered, and laid out for a particular presentation.

**Owns**

- filtering;
- grouping;
- sorting;
- time-window selection;
- layout configuration;
- visibility;
- view parameters;
- annotation placement;
- presentation-specific semantic projection choices that are not styling.

**Invariants**

A View MUST NOT change project semantics or scheduling results.

**Does not own**

Colors, fonts, scheduling semantics, or renderer-specific scene state.

---

### 5.9 `07-style-and-theme.md`

**Purpose**

Defines the boundary between semantic visual rules and concrete visual design.

**Owns**

**Style**

- semantic selectors;
- semantic-to-visual projection;
- appearance roles;
- style composition and cascade;
- style resolution.

**Theme**

- colors;
- typography;
- widths;
- spacing;
- concrete sizes;
- concrete appearance tokens;
- theme inheritance.

The intended separation is:

```text
Project = What
View    = Which / Where
Style   = How
Theme   = Look
```

**Does not own**

Project semantics, scheduling, or renderer-specific state.

---

### 5.10 `08-scene-and-rendering.md`

**Purpose**

Defines the renderer-neutral scene representation and the projection from semantic objects into visual primitives.

**Owns**

- scene primitives;
- Rect;
- Symbol;
- Line/Path;
- Text;
- Group;
- scene identity;
- projection rules;
- renderer interface;
- coordinate mapping;
- temporal scale projection;
- export expectations;
- tldraw integration boundary;
- SVG and future renderer boundaries.

**Invariants**

- Scene state is derived state.
- Scene coordinates are not authoritative temporal data.
- tldraw Store is not the project source of truth.

---

### 5.11 `09-application-architecture.md`

**Purpose**

Defines the major runtime components and their responsibilities.

**Owns**

Components such as:

```text
Project Store
Profile Registry
Temporal Engine
Scheduling Engine
Transform Engine
Predicate Engine
View Engine
Style Resolver
Scene Builder
Command Engine
Renderer adapters
```

It also owns major data flows, component boundaries, runtime sequencing, persistence boundaries, and implementation-level dependency direction.

**Does not own**

Semantics already defined by the specifications.

---

### 5.12 `10-command-model.md`

**Purpose**

Defines the semantic mutation interface shared by interactive UI, CLI, automation, and AI agents.

**Owns**

Commands such as:

- create/delete object;
- set semantic field;
- move temporal object;
- resize span;
- connect/disconnect objects;
- modify schedule;
- add/edit annotation.

Also owns:

- validation boundaries;
- command results;
- undo/redo semantics;
- batching/transactions;
- semantic change representation;
- relationship to semantic Git diff.

The intended architecture is:

```text
GUI ─┐
CLI ─┼─> Command -> Project Model
AI  ─┘
```

---

### 5.13 `11-extension-model.md`

**Purpose**

Defines how the semantic model can be extended without turning the core into a generic graph or rendering system.

**Owns**

- custom profiles;
- typed custom fields;
- custom entities;
- custom relation profiles;
- derived fields;
- domain packages;
- profile inheritance;
- validation of extensions;
- fallback behavior;
- declarative extension boundaries;
- code-plugin boundaries.

A key boundary is:

```text
Semantic extension  -> declarative data/schema
Rendering extension -> code/plugin
```

Scheduling semantics MUST NOT become arbitrarily programmable through untrusted data extensions.

---

### 5.14 `12-quality-and-invariants.md`

**Purpose**

Defines system-wide qualities and architectural invariants against which designs and implementations can be reviewed.

Initial invariants include:

1. Project files MUST produce meaningful Git diffs.
2. Project semantics MUST NOT depend on View, Style, Theme, Scene, or renderer.
3. Scene coordinates MUST NOT be the source of truth for temporal placement.
4. Rendering MUST be reproducible from Project + View + Style + Theme + explicit RenderContext.
5. Temporal calculations MUST be deterministic for the same inputs and context.
6. Unknown profiles SHOULD degrade through their nearest supported ancestor when possible.
7. Domain data MUST remain usable without tldraw.
8. User expressions MUST NOT execute arbitrary code.
9. Presentation changes MUST NOT silently mutate semantic project data.
10. Serialization shorthand MUST normalize to an unambiguous semantic representation.

This document SHOULD increasingly use testable scenarios rather than vague quality adjectives.

---

### 5.15 `13-presentation-format.md`

**Purpose**

Defines persistent syntax, normalization, and resource composition for downstream
Presentation and Application definitions without changing the Core Project Format.

**Owns**

- common resource envelope and versioning;
- View, Style, Theme, Render Context, and Scene-profile resource references;
- Snapshot-reference and Actual-observation-set persistence boundaries;
- Command envelope persistence boundary;
- resource-ID, reference, and composition normalization; and
- handoff to schemas and canonical fixtures.

**Does not own**

Core Project semantics or syntax, View/Style/Theme/Scene meaning, Command semantics,
renderer output, or GUI state persistence.

## 6. Supporting Artifact Types

### 6.1 Architecture Decision Records

ADRs record significant decisions and their rationale.

Initial likely ADRs include:

```text
ADR-0001-use-half-open-temporal-intervals
ADR-0002-separate-temporal-point-and-span
ADR-0003-model-dependencies-by-endpoints
ADR-0004-separate-domain-model-from-project-format
ADR-0005-tldraw-is-not-source-of-truth
ADR-0006-separate-view-style-and-theme
ADR-0007-use-distinct-temporal-amount-types
ADR-0008-model-working-days-separately-from-calendar-days
ADR-0009-use-command-layer-for-semantic-mutations
ADR-0010-support-profile-based-semantic-extension
```

An ADR SHOULD be created when a decision is difficult to reverse, materially constrains later design, resolves competing plausible alternatives, or establishes an important architectural boundary.

Minor details do not require ADRs.

### 6.2 Schemas

Machine-readable schemas SHOULD validate the persistent representation and extension definitions.

Schemas MAY include:

- project schema;
- profile schema;
- view schema;
- style schema;
- theme schema;
- extension-field schema.

Schema structure SHOULD follow the semantic specification rather than becoming an independent domain model.

### 6.3 Examples

Examples SHOULD progress from minimal to representative.

Initial target set:

```text
examples/
├── minimal.yaml
├── dependencies.yaml
├── calendar.yaml
├── roadmap.yaml
├── semiconductor.yaml
├── custom-profile.yaml
└── full-example.yaml
```

Examples SHOULD cover both common behavior and important edge cases.

Where practical, examples SHOULD be executable fixtures.

## 7. Source-of-Truth Rules

The authoritative ownership hierarchy is:

| Concern | Authoritative artifact |
|---|---|
| Product intent and scope | Vision |
| Vocabulary | Concepts |
| Semantic object model | Domain Model |
| Meaning of time and temporal arithmetic | Temporal Model |
| Scheduling semantics | Scheduling Model |
| Persistent syntax and normalization | Project Format |
| Presentation/application definition syntax and normalization | Presentation Format |
| Selection and layout | View Model |
| Semantic visual mapping | Style |
| Concrete visual values | Theme |
| Visual primitive projection | Scene and Rendering |
| Runtime/component implementation | Application Architecture |
| Semantic mutations | Command Model |
| Extension rules | Extension Model |
| Cross-system invariants | Quality and Invariants |
| Decision rationale/history | ADR |
| Machine-checkable structure | Schemas |
| Canonical behavior illustrations | Examples |

If two artifacts disagree, the artifact that owns the relevant concern MUST be corrected or treated as authoritative for that concern.

An ADR does not override the current specification merely because it is older or more detailed. It explains how the current design was reached.

## 8. Dependency Direction

Normative design dependencies SHOULD flow primarily in one direction:

```text
Vision
  ↓
Concepts
  ↓
Domain Model
  ↓
Temporal Model
  ↓
Scheduling Model
  ↓
Project Format

Domain / Temporal / Scheduling
  ↓
View
  ↓
Style / Theme
  ↓
Scene / Rendering

Core + Presentation
  ↓
Application Architecture
  ↓
Command/runtime implementation
```

The exact ordering between Domain Model and Temporal Model is not a semantic dependency claim: the Domain Model refers to temporal concepts while the Temporal Model deliberately avoids project-domain semantics. Cross-references are therefore expected, but circular redefinition is not.

Extension Model and Quality/Invariants are cross-cutting and may reference multiple layers.

## 9. Specification Language

The documents use the following normative terms:

- **MUST / MUST NOT** — required for conformance;
- **SHOULD / SHOULD NOT** — expected unless a documented reason justifies deviation;
- **MAY** — optional.

Design proposals that are not yet accepted SHOULD be explicitly marked as such and MUST NOT be written as normative requirements.

Examples are illustrative unless explicitly labeled normative.

## 10. Document Status and Maturity

Each major design artifact SHOULD declare a status.

Initial states:

```text
Draft
  ↓
Proposed
  ↓
Stable
  ↓
Deprecated
```

### Draft

Actively being developed. Significant changes are expected.

### Proposed

Semantics are considered coherent and ready for focused review.

### Stable

Accepted as the current design contract. Breaking changes require explicit review and usually an ADR.

### Deprecated

Retained for transition or historical reference but no longer recommended for new use.

A version number MAY also be used where external compatibility matters, particularly for Project Format and schemas.

## 11. Change Process

A design change SHOULD follow this sequence:

```text
Identify affected semantic owner
          ↓
Update or propose the normative specification
          ↓
Record an ADR if the decision is architecturally significant
          ↓
Update schemas
          ↓
Update canonical examples
          ↓
Update dependent specifications
          ↓
Update implementation and tests
```

Changes SHOULD be reviewed for impact across document boundaries rather than mechanically updating every document.

For example, changing the meaning of `3wd` requires review of:

- Temporal Model;
- Scheduling Model;
- Project Format examples;
- schemas;
- scheduler tests.

It does not necessarily require changes to View or Theme.

## 12. Design Review Rules

A design review SHOULD ask at least:

1. Which artifact owns this concept?
2. Is the proposal semantic, representational, presentational, or implementation-specific?
3. Does it introduce duplicate authority?
4. Does it preserve deterministic behavior?
5. Does it preserve meaningful Git representation?
6. Can the concept be validated or demonstrated by schema/example?
7. Does it accidentally couple the domain to tldraw or another renderer?
8. Does it belong in the Core or in an extension/profile?
9. Is the decision difficult enough to reverse that an ADR is warranted?
10. Does the change preserve the documented invariants?

## 13. Initial Design Deliverables

The first design milestone is **Core Specification v0.1**.

The initial writing order SHOULD be:

```text
1. 00-vision.md
2. 01-concepts.md
3. 02-domain-model.md
4. 03-temporal-model.md
5. 04-scheduling-model.md
6. 05-project-format.md
7. 12-quality-and-invariants.md
8. Initial ADR set
9. Initial schemas
10. Initial executable examples
```

Presentation and application architecture documents SHOULD follow after the Core Specification is internally coherent.

The ordering is intentional: implementation structure SHOULD follow semantic design rather than constrain it prematurely.

## 14. Core Specification v0.1 Definition of Done

Core Specification v0.1 is complete when:

- the core semantic primitives are explicitly defined;
- Point and Span temporal semantics are unambiguous;
- temporal amount types and arithmetic are defined;
- calendar behavior required by Core scheduling is defined;
- scheduling placement modes are defined;
- endpoint and dependency semantics are defined;
- constraint and deadline semantics are defined;
- persistent representation exists for all Core concepts;
- normalization and shorthand rules are unambiguous;
- important invalid states are specified;
- at least one minimal and one dependency/calendar example validate against the schema;
- major architectural decisions have corresponding ADRs;
- the Quality and Invariants document can be used to review an implementation;
- no Core semantic rule depends on tldraw, SVG, or another presentation technology.

Core Specification v0.1 does **not** require:

- a complete GUI design;
- a production renderer;
- PPTX export;
- collaboration;
- resource scheduling;
- cost tracking;
- timesheets;
- arbitrary user-defined scheduling logic.

## 15. Subsequent Design Phases

After Core Specification v0.1:

```text
Phase 2 — Presentation Specification
  View
  Style
  Theme
  Scene / Rendering

Phase 3 — Application Architecture
  Components
  Command Model
  Runtime flows
  persistence integration
  editor integration

Presentation persistence and fixture gate
  View / Style / Theme / Render Context format
  Snapshot / Actual format
  Command envelope format
  schemas and canonical fixtures

Phase 4 — Extensibility
  Profiles
  domain packages
  derived fields
  plugin boundaries

Phase 5 — Implementation specifications
  tldraw adapter
  SVG exporter
  CLI
  AI command interface
  optional PPTX exporter
```

These phases MAY overlap experimentally, but normative dependencies SHOULD continue to point toward the Core rather than allowing implementation prototypes to silently redefine it.

## 16. Guiding Boundary

The central documentation boundary is:

```text
                SEMANTIC SOURCE OF TRUTH

 Project + Profiles + Temporal/Scheduling semantics
                         │
                         ▼
                    Project Format
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
        Commands / AI             Views
                                     │
                                     ▼
                                   Style
                                     │
                                     ▼
                                   Theme
                                     │
                                     ▼
                                   Scene
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                       tldraw       SVG       future
```

The design documentation SHALL preserve this boundary unless an explicit architectural decision replaces it.

The project is not defined by its current renderer. It is defined by its semantic project model, temporal and scheduling rules, durable representation, and deterministic projection into presentation forms.
