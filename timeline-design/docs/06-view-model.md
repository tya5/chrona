# View Model

**Status:** Draft  
**Depends on:** `01-concepts.md`, `02-domain-model.md`, `03-temporal-model.md`, `04-scheduling-model.md`, `05-project-format.md`  
**Owns:** selection, comparison context, grouping, ordering, temporal-window selection, visibility, layout intent, and presentation annotations.

## 1. Purpose

A View is a reproducible presentation projection over a semantic Project. It answers **which** information is shown and **where it is arranged**. A View does not change the meaning of a Project object, date, dependency, schedule, Snapshot, or Actual observation.

```text
Project  = What exists and what it means
View     = Which information is shown and where it is arranged
Style    = How selected information is expressed visually
Theme    = Concrete visual tokens
Scene    = Renderer-neutral visual primitives
```

### 1.1 Design drivers from prior research

Chrona is not a generic project-management suite, a Mermaid-only diagram DSL, a slideware clone, or a pixel-authoritative canvas. Existing tools expose complementary but insufficient trade-offs:

- project-management and Gantt tools commonly add workflow, resources, cost, and portfolio machinery that is outside Chrona's purpose;
- Git-friendly diagram DSLs preserve reviewability but do not provide enough timeline annotation and presentation freedom;
- canvas editors such as tldraw are valuable future interaction surfaces, but their scene state would create noisy diffs if it became the Project source of truth; and
- slide tools provide expressive callouts and emphasis but hide schedule semantics inside geometry.

The View Model therefore preserves semantic, Git-reviewable Project data while allowing multiple review-focused projections, named comparisons, and anchored presentation annotations. Its purpose is to make semantic changes visible without turning presentation state into the model.

## 2. Invariants

- A View MUST NOT mutate Project data, scheduling results, Snapshot data, or Actual observations.
- A View MUST NOT make Actual observations scheduling inputs or infer a rescheduling policy from them.
- A View MUST identify Project objects by stable project-local IDs, never by title, visual position, or renderer identity.
- A View MUST be reproducible from explicit input references and View parameters.
- A View MUST NOT own colors, fonts, stroke widths, renderer-specific state, or absolute scene coordinates.
- Omitting an item from a View MUST NOT delete or alter the underlying semantic item.

## 3. View Context

A View is evaluated against an explicit View Context.

| Input | Meaning | Required |
|---|---|---|
| Primary Project | Semantic project data and its derived planned schedule | Yes |
| Snapshot | Named immutable comparison state, potentially identified by a Git ref | No |
| Actual observations | Observed start, finish, point occurrence, and progress | No |
| Render context | Explicit evaluation date, locale, and other environment data | As required by the consumer |

The primary Project is required. Snapshot and Actual inputs MUST be named when present. A View or renderer MUST NOT silently select “latest”, “main”, or a local-clock date as a comparison source.

Serialization for Views, Snapshots, and Actual observations is outside this document. The View Model defines their presentation semantics only.

## 4. View Definition

A View definition is declarative. Its eventual YAML syntax belongs to the Project Format or a future View schema.

| Concern | View responsibility |
|---|---|
| Selection | Include or exclude objects, relations, entities, and annotations |
| Grouping | Partition selected objects into lanes from semantic fields |
| Ordering | Deterministically order groups and objects |
| Temporal window | Select the presented time interval |
| Comparison | Select the Primary Project, named Snapshot, and/or Actual input |
| Visibility | Select labels, relations, annotations, and comparison facets |
| Layout intent | Choose lanes, hierarchy expansion, compactness, and annotation anchoring |

Selection expressions MUST be declarative predicates over semantic data and MUST NOT execute arbitrary host-language code.

## 5. Projection Pipeline

The View pipeline is separate from styling and scene construction.

```text
Project + Schedule + View Context
              │
              ▼
          Selection
              │
              ▼
    Grouping / Ordering / Window
              │
              ▼
       View Projection (semantic)
              │
              ▼
       Style / Theme / Scene
```

A View Projection contains stable object IDs, resolved temporal placements, comparison facets, lane membership, order, temporal window, and annotation-placement intent. It does not contain rectangles, pixels, paths, fonts, or colors.

## 6. Selection, Grouping, and Ordering

Selection identifies semantic items eligible for presentation. A View MAY select by stable object ID, type, hierarchy, entity reference, profile, or typed extension field.

Relations MAY be shown only when both endpoints are selected. A View MAY retain an omitted endpoint as a non-rendered explanatory boundary, but MUST NOT invent a relation absent from the Project.

Semantic dependencies and explanatory arrows are distinct. A semantic dependency is owned by the Project and constrains or validates scheduling. An explanatory arrow is a View-local presentation annotation; it MAY explain a risk, decision, or causal narrative but MUST NOT create a scheduling constraint.

Grouping creates presentation lanes; it is not semantic containment. A View MAY group by team, component, owner, status, object type, or another semantic field. Within a group, ordering MUST be deterministic. Valid keys include stable ID, title, planned start/end, selected extension field, or explicit View-local order. A missing key MUST use a documented fallback rather than host iteration order.

## 7. Temporal Window

A View selects a temporal window independently from scheduling semantics. A window MAY be explicit, derived from selected planned placements, derived from a named comparison input, or expanded by an explicit presentation margin.

Date-based Views use the Date temporal domain. DateTime View behavior is deferred until a corresponding Core scheduling profile exists. Human-facing inclusive end-date display is a View or renderer concern and MUST NOT alter Core half-open span semantics.

## 8. Comparison Views

A comparison is a named relation between independently identified states; it is not a mutable field added to every Project object.

### 8.1 Current versus Snapshot

Current-versus-Snapshot compares the Primary Project with an immutable named Snapshot. A Snapshot MAY ultimately be represented by a Git ref. Alignment uses stable project-local IDs. A missing object is a comparison result, not an instruction to create or delete an object.

### 8.2 Plan versus Actual

Plan-versus-Actual compares planned placements from the Primary Project or named Snapshot with independent Actual observations. Actual observations MAY contain actual start, finish, point occurrence, and progress. They MUST NOT automatically change planned dependencies, duration, forecast, or schedule.

The View Projection MAY expose planned and actual endpoints, start/finish delta, progress, absent observation, and unmatched observation. Whether an actual delay triggers rescheduling belongs to a future scheduling or application policy.

### 8.3 Comparison Alignment

Comparison alignment MUST use stable IDs. A renamed title, regrouped object, or changed visual placement remains the same comparison subject. An unknown reference MUST produce a comparison diagnostic and MUST NOT be matched by text similarity.

## 9. Annotations and Layout Intent

Semantic annotations remain Project data and are selected with their anchors. Presentation annotations are View-local callouts, highlights, notes, or explanatory arrows. They MAY anchor to a selected object, relation, group, or temporal coordinate. The View owns the stable anchor and logical placement preference; Scene and Rendering own any concrete relative offset or coordinate. Deleting a presentation annotation MUST NOT alter a Project object, semantic annotation, or dependency.

Layout intent includes lane assignment, collapsed groups, hierarchy expansion, preferred compactness, and annotation anchoring. It is not renderer geometry.

## 10. Diagnostics

View evaluation SHOULD report stable diagnostics for unknown Project, Snapshot, Actual, or object references; incompatible temporal domains; duplicate comparison identity; and invalid explicit windows. Exact identifiers and schema are deferred to the View schema and Application Architecture work.

## 11. Out of Scope

This document does not define YAML persistence; colors, typography, or line styles; scene primitives or coordinates; SVG/tldraw adaptation; editing commands; snapshot capture; actual-driven rescheduling; resource leveling; or DateTime scheduling.

## 12. Boundary to Subsequent Documents

`07-style-and-theme.md` may assume that a View Projection exposes selected objects, comparisons, lanes, order, temporal window, and annotation intent. It MUST NOT redefine selection or comparison semantics.

`08-scene-and-rendering.md` may transform a styled View Projection into scene primitives. It MUST NOT become the source of object identity, temporal truth, or comparison alignment.
