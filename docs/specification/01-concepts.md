# Core Concepts

**Status:** Proposed  
**Core Specification:** v0.1

## 1. Project

A **Project** is the semantic source of truth for a set of project objects, relations,
entities, annotations, calendars, profiles, and extension data.

A Project does not contain renderer coordinates as authoritative temporal state.

## 2. Semantic object

A semantic object has stable identity and project meaning independent of a particular
view.

Core semantic primitives are:

```text
TemporalPoint
TemporalSpan
Entity
Relation
Annotation
```

## 3. TemporalPoint

A **TemporalPoint** occupies one coordinate in a temporal domain.

It is not modeled as a zero-length span.

Examples of profiles based on a point include milestone, deadline, release, gate, and
reference marker.

## 4. TemporalSpan

A **TemporalSpan** occupies a non-empty half-open temporal interval:

```text
[start, end)
```

Examples of profiles based on a span include task, phase, freeze, evaluation window,
and availability window.

## 5. Entity

An **Entity** is a non-temporal semantic object that can participate in project
relationships or typed references.

Examples include team, component, product, customer, and person.

Entities are not placed on the timeline merely because they exist.

## 6. Relation

A **Relation** is a first-class semantic relationship between project objects.

A dependency is a profile of Relation with scheduling semantics. Other relation
profiles MAY be purely semantic and have no scheduling effect.

A decorative arrow is not a Relation unless it expresses project meaning.

## 7. Annotation

An **Annotation** expresses information associated with the project but not reducible
to a temporal object or relation.

Semantic annotations belong to the Project. Presentation-only callouts or arrows may
belong to a View.

## 8. Profile

A **Profile** specializes a known semantic primitive.

Examples:

```text
task       : TemporalSpan
phase      : TemporalSpan
milestone  : TemporalPoint
gate       : milestone
dependency : Relation
team       : Entity
```

A profile MAY add typed fields, constraints, derived fields, and permitted
relationships. It MUST ultimately inherit from a supported core primitive.

## 9. Temporal coordinate

A temporal coordinate is a position in a temporal domain.

Core v0.1 defines two coordinate domains:

- `Date`
- `DateTime`

They are distinct types and are not implicitly mixed.

## 10. Temporal amount

A temporal amount describes movement along time.

Core v0.1 distinguishes:

```text
ExactDuration   physical elapsed time
CalendarPeriod  calendar-relative amount
WorkPeriod      discrete working-day amount
```

These types are intentionally not freely interchangeable.

## 11. Calendar

A **Calendar** determines which dates are valid working dates for `WorkPeriod`
arithmetic and scheduled placement.

Core v0.1 models working dates, not resource-hour capacity.

## 12. Temporal placement

A temporal object obtains its position using one of three placement modes:

- **fixed** — authoritative temporal coordinates are supplied;
- **derived** — coordinates are derived from other semantic state;
- **scheduled** — coordinates are solved from anchors, duration, dependencies,
  constraints, and calendars.

## 13. Endpoint

An **Endpoint** is a relation-addressable temporal coordinate on an object.

Core endpoints are:

```text
TemporalPoint: at
TemporalSpan:  start, end
```

## 14. Bound

A **Bound** constrains an endpoint.

```text
lower bound: endpoint >= value
upper bound: endpoint <= value
```

Dependencies and explicit constraints can both be normalized to bounds.

## 15. Deadline

A **Deadline** records a target date or point that may be compared with a schedule but
does not itself constrain the scheduler.

A deadline is therefore distinct from an upper bound.

## 16. View, Style, Theme, Scene

These are downstream presentation concepts.

```text
Project = What exists and what it means
View    = Which information is shown and where it is arranged
Style   = How semantics map to visual roles
Theme   = Concrete visual values
Scene   = Renderer-neutral visual primitives
```

None of them may redefine Core scheduling semantics.

## 17. Presentation composition vocabulary

An **Actual** is an independently observed fact aligned explicitly to a Project object;
it never reschedules the plan. An **Observation** is attributed read-only evidence and
is not automatically an Actual.

A **Surface** is one public presentation projection. A Surface is divided into named
**Regions** and **Slots**. A Slot binds one declared content source; a **Track** is one
allocation axis inside a Region. A **Lane** is a deterministic placement band for
overlapping temporal items. A **Facet** distinguishes planned, Actual, baseline, or
variance meaning without changing object identity. **Detail** supplies labels,
explanations, legends, and bounded review panels.

A **Layout Profile** is the v0.2 intent-oriented composition resource. It owns the
stable-node composition tree but not concrete Theme values or selected facts. Theme and
Layout are reusable independent resources bound by Render Context v0.4; renderers consume
only a completed Scene.

A **Render Context** is the immutable entry for one reproducible presentation
evaluation. Its **evaluation closure** is the ordered set of pinned resources and
content identities needed for that evaluation. It never means “use the current files”.

## 18. Snapshot

A **Snapshot** identifies a comparison state of a Project, potentially by a Git
reference or embedded immutable data.

Snapshots are intended for comparison such as baseline-versus-current. Core v0.1
defines the concept but does not yet standardize full snapshot serialization.
