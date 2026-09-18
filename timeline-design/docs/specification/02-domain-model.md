# Domain Model

**Status:** Proposed  
**Core Specification:** v0.1

## 1. Scope

This document defines semantic project objects independently of temporal arithmetic,
persistent syntax, views, and rendering.

## 2. Identity

Every addressable project object MUST have a stable project-local identifier.

Identifiers:

- MUST be unique within their namespace;
- SHOULD remain stable across title changes and schedule movement;
- MUST NOT be derived from renderer coordinates;
- SHOULD be suitable for Git review and semantic references.

Titles and display labels are not identifiers.

## 3. Core primitives

```text
SemanticObject
├── TemporalPoint
├── TemporalSpan
├── Entity
├── Relation
└── Annotation
```

The core deliberately does not define `Task` or `Milestone` as bottom-level
primitives. Those are standard profiles.

## 4. TemporalPoint

A TemporalPoint has:

- stable identity;
- profile/type;
- one temporal placement;
- typed semantic fields.

Its temporal endpoint is `at`.

A point MUST NOT be represented as a span with identical start and end coordinates.

## 5. TemporalSpan

A TemporalSpan has:

- stable identity;
- profile/type;
- one temporal placement;
- typed semantic fields.

Its temporal endpoints are `start` and `end`.

A resolved span MUST satisfy:

```text
start < end
```

under its temporal domain.

The occupied interval is `[start, end)`.

## 6. Entity

An Entity has stable identity, profile/type, title/label as applicable, and typed
semantic fields.

Entity references SHOULD be used when a concept has identity and may be shared by
multiple temporal objects. Repeating arbitrary strings for such concepts is
discouraged when stable references are useful.

## 7. Relation

A Relation has:

- stable identity where independently addressable;
- profile/type;
- source reference;
- target reference;
- typed relation fields.

Relations MAY connect temporal objects, entities, or other supported semantic objects
as permitted by their profile.

A dependency relation additionally addresses temporal endpoints and is specified by
the Scheduling Model.

## 8. Annotation

Annotations are separated into two conceptual classes:

### 8.1 Semantic annotation

Project information that should survive changes of view.

Example: “Customer approval required at EVT.”

### 8.2 Presentation annotation

Information specific to a presentation or meeting.

Example: “Discuss this risk in Friday review.”

Only semantic annotations belong to the Core Project model. Presentation annotation
is owned by the View model.

A semantic annotation MAY anchor to:

- a semantic object;
- a temporal point;
- a temporal range;
- a relation;
- another supported semantic anchor.

Pixel coordinates are not semantic anchors.

## 9. Profiles

Profiles provide semantic specialization without expanding the core primitive set.

A profile definition has, conceptually:

```text
id
extends
fields
constraints
derived fields
allowed relationships
```

Inheritance MUST terminate at one of the core primitives.

Example hierarchy:

```text
TemporalPoint
└── milestone
    ├── gate
    └── release

TemporalSpan
├── task
└── phase
```

Unknown profiles SHOULD degrade through their declared parent profile when a consumer
does not understand the specialization.

## 10. Standard profile library

Core v0.1 assumes an initial standard library containing at least:

```text
task        extends TemporalSpan
phase       extends TemporalSpan
milestone   extends TemporalPoint
deadline    extends TemporalPoint
dependency  extends Relation
```

`gate`, `release`, and domain-specific vocabulary may be supplied as standard or
optional domain profiles without changing the core primitives.

## 11. Typed extension fields

Extension data SHOULD be declared by schema rather than stored only as unconstrained
metadata.

Initial field types are expected to include:

```text
string
number
boolean
date
datetime
temporal amount
enum
tags
object reference
object reference[]
```

A future extension MAY add additional serializable types while preserving deterministic
validation.

## 12. Hierarchy and grouping

Semantic hierarchy and visual grouping are different concepts.

A parent/child relationship, if used, is semantic project structure.

Grouping by team, component, owner, status, or another field is normally a View
operation and MUST NOT require mutating semantic hierarchy.

## 13. Derived semantic state

Derived fields MAY enrich the semantic model with deterministic values such as:

- duration;
- remaining duration;
- variance;
- overdue;
- slack;
- critical;
- schedule conflict;
- presence of delayed predecessors.

Complex graph or scheduling computation SHOULD be performed before predicate/style
evaluation rather than embedded as arbitrary graph traversal inside selectors.

## 14. Domain invariants

- Semantic identity is independent of presentation.
- A Point and a Span are distinct types.
- A resolved Span is non-empty.
- Profiles extend known semantics rather than replacing them.
- View grouping is not semantic hierarchy.
- Decorative graphics are not semantic Relations.
- Renderer state is not domain state.
