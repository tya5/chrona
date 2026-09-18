# Vision and Scope

**Status:** Proposed  
**Core Specification:** v0.1

## 1. Problem

Project timelines are often communicated with slide tools because they make it easy
to create readable schedules, milestones, dependency arrows, callouts, highlights,
and presentation-specific emphasis.

Those documents are effective presentations but poor structured project data:

- changes are difficult to review as meaningful Git diffs;
- schedule data is hard to reuse in another view;
- semantic relationships are hidden in drawing geometry;
- automation and AI agents must infer meaning from presentation artifacts;
- the same underlying plan is duplicated across engineering, executive, and customer views.

Traditional project-management systems solve some structural problems but commonly
bring substantially more workflow, resource, and portfolio machinery than is required
for a concise project line chart.

## 2. Vision

Create a **Git-friendly, structured, extensible temporal visualization model** that
combines reusable project semantics with presentation freedom.

The semantic source of truth is text-based and machine-readable. Multiple views and
renderers project the same project model without redefining its meaning.

The system is centered on time-bearing project information rather than on generic
diagramming or full project-management operations.

## 3. Goals

The system SHOULD provide:

- human-readable project source files;
- meaningful line-oriented Git diffs;
- stable semantic identifiers;
- deterministic temporal and scheduling semantics;
- first-class points, spans, relations, entities, and annotations;
- dependency and calendar semantics suitable for project timelines;
- reusable data across multiple views;
- declarative semantic extension through profiles and typed fields;
- deterministic projection into interactive and export renderers;
- a semantic command boundary usable by GUI, CLI, automation, and AI agents;
- enough presentation freedom for milestones, callouts, dependency lines, highlights,
  and similar line-chart communication.

## 4. Non-goals

Core v0.1 is not intended to provide:

- resource leveling or resource-capacity optimization;
- timesheets;
- earned-value or cost accounting;
- ticket/workflow management;
- permissions or collaboration infrastructure;
- generic graph editing;
- arbitrary code execution in project files;
- a PowerPoint clone;
- a full Microsoft Project or Primavera replacement;
- renderer-specific persistence as the project source of truth.

## 5. Product principles

### 5.0 Independent ownership, integrated review

Chrona SHOULD allow a program timeline to reference approved summaries from separately
owned subprojects without making their source files shared mutable state. This is a
reproducible presentation and interface boundary, not a centralized portfolio or work
management system.

### 5.1 Semantics before rendering

Project meaning SHALL remain valid without a particular UI or renderer.

### 5.2 Structured but not rigid

The core semantic model SHALL remain small. Domain-specific vocabulary SHOULD be
introduced through profiles and typed extension fields rather than by continuously
expanding the core.

### 5.3 Time-axis centered

The system MAY expose graph, hierarchy, or other projections, but its core purpose is
the representation and visualization of project information in time.

### 5.4 Git-native

Canonical project representation SHOULD minimize incidental reordering, duplicated
derived values, opaque binary state, and renderer-generated noise.

### 5.5 Agent-operable

An AI agent SHOULD be able to inspect, validate, and mutate the semantic model without
reverse-engineering pixels or proprietary document structure.

### 5.6 Deterministic

Given the same semantic inputs and explicit evaluation context, scheduling and
rendering SHOULD produce the same result.

## 6. Primary use cases

Representative use cases include:

- engineering development line charts;
- release and roadmap timelines;
- semiconductor development schedules containing gates such as EVT/DVT/PVT;
- customer-facing schedule projections derived from engineering data;
- plan-versus-actual visualization;
- semantic review of schedule changes in Git;
- AI-assisted schedule edits through structured commands.

## 7. Architectural boundary

```text
Semantic Project
      │
      ├── Profiles / Extensions
      ├── Temporal semantics
      └── Scheduling semantics
      │
      ▼
Persistent Project Format
      │
      ▼
Views / Styles / Themes
      │
      ▼
Renderer-neutral Scene
      │
      ├── Interactive editor
      ├── SVG
      └── future exporters
```

Core Specification v0.1 ends primarily at the persistent semantic project format.
Presentation and application architecture build on this boundary.
