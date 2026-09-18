# Application Architecture

**Status:** Proposed
**Depends on:** Core Specification (`01`–`05`), Presentation Specification (`06`–`08`)
**Constrained by:** [12 Quality and Invariants](12-quality-and-invariants.md)
**Owns:** runtime component responsibilities, dependency direction, evaluation and mutation flows, persistence boundaries, derived-state lifecycle, and adapter boundaries.

## 1. Purpose

This document defines how an application realizes Chrona's existing semantic and presentation specifications without creating a second authority for them. It is an architecture for a Git-friendly temporal visualization system, not an architecture for a general project-management service.

Application Architecture decides which component evaluates or transports each specification. It does **not** redefine object semantics, temporal arithmetic, scheduling rules, View selection, visual roles, Scene primitives, or command semantics.

## 2. Architectural principles

- Canonical semantic data remains usable as structured files without an editor, renderer, or service process.
- Derived state is rebuilt from versioned inputs and explicit evaluation context; it is never silently persisted as semantic truth.
- Read evaluation flows in the direction `Project → Schedule → View → Style/Theme → Scene → Renderer`.
- All mutation clients—including CLI, GUI, automation, and AI agents—use the Command Engine boundary. They do not patch derived state or renderer stores directly.
- Components exchange typed data and stable diagnostics, not ad-hoc dictionaries whose meaning depends on a caller.
- A renderer, canvas store, cache, or local runtime default must not become an implicit source of project, comparison, or scheduling state.

## 3. Component model

### 3.1 Components and responsibilities

| Component | Responsibility | Must not own |
|---|---|---|
| Project Store | Load, normalize, identify, and persist canonical Project revisions | Temporal interpretation, scheduling, or rendering |
| Evaluation Closure Resolver | Resolve and verify the immutable resource/package closure named by a Render Context | Fallback to current files, branches, or host defaults |
| Federation Resolver | Resolve pinned child timeline exports and compose read-only summary inputs | Loading a child branch tip, editing child data, or treating a raw child Project as a parent resource |
| Profile Registry | Resolve supported core and extension profiles, typed fields, and schemas | Arbitrary executable extension behavior |
| Temporal Engine | Parse and operate on temporal values and calendars | Project mutation policy or visual layout |
| Scheduling Engine | Validate and derive planned placements under the Scheduling Model | Actual-driven rescheduling or presentation decisions |
| Transform / Predicate Engine | Evaluate declarative selection, grouping, ordering, and comparison predicates | Host-language expression execution or geometry |
| View Engine | Build a semantic View Projection from explicit state and View Context | Colours, fonts, primitive coordinates, or project mutation |
| Style Resolver | Resolve semantic selectors to visual roles | Scheduling, geometry, or literal token values |
| Theme Resolver | Resolve role token references to concrete visual values | Semantic selection or role conditions |
| Scene Builder | Produce positioned, metadata-preserving Scene primitives | Semantic source data or renderer-owned layout conventions |
| Renderer Adapter | Translate a completed Scene to SVG, canvas, or another declared target | Semantic inference or canonical state mutation |
| Command Engine | Apply validated semantic or presentation-definition mutations as new revisions | Renderer-specific interaction behavior or scheduling semantics |
| Runtime Coordinator | Bind explicit inputs, invoke components in dependency order, collect diagnostics, and manage derived caches | Hidden policy changes or alternate semantic rules |

The Command Engine's command vocabulary, transactions, undo/redo, and mutation result semantics belong to [10 Command Model](10-command-model.md). This document only defines its placement and integration boundary.

### 3.2 Dependency direction

```text
Canonical files / revision references
                ↓
 Project Store ──→ Profile Registry
        │                 │
        └──────→ Temporal Engine
                         ↓
                   Scheduling Engine
                         ↓
 Transform / Predicate → View → Style → Theme → Scene → Renderer adapters

CLI / GUI / AI / automation → Command Engine → Project Store
```

Dependencies point toward lower-level semantics and then outward toward presentation. A renderer adapter must never depend on the Project Store to infer missing data, and the Scheduling Engine must never depend on a View, Theme, Scene, or renderer.

## 4. State ownership and persistence boundaries

| State category | Authoritative owner | Persistence rule |
|---|---|---|
| Project, profiles, calendars, semantic annotations, and relations | Project Store | Canonical, reviewable structured source data |
| Named Snapshot and Actual input references | Their specified persistence model | Explicitly named, immutable or independently observed input; never inferred as “latest” |
| Federation Plan and child export | Parent plan / child Project repository | Immutable, read-only export consumed through a parent-owned pinned plan reference; never merged into parent canonical data |
| View, Style, Theme, and Scene-profile definitions | Their respective specifications | Declarative versioned data; serialization syntax may evolve independently |
| Schedule result, View Projection, resolved Style/Theme, Scene, SVG, canvas store | Runtime Coordinator / adapters | Derived cache or output only; invalidated when any declared input changes |
| Diagnostics, manifests, and trace data | Runtime Coordinator | Inspectable output; not a substitute for canonical source |

The Project Store assigns or resolves a revision identity for every load and write. Evaluation and rendering requests bind that identity, so a schedule, View Projection, and Scene from different Project revisions cannot be combined accidentally.

## 5. Read evaluation flow

### 5.1 Evaluation request

Every read evaluation begins with an explicit request containing at least:

- a Render Context that names the primary Project revision, View, Style, Theme, Scene
  profile, and named Snapshot and Actual inputs when used;
- its explicit locale, viewport, target capabilities, and layout metrics; and
- optional requested output artifact.

The Runtime Coordinator delegates resolution to the Evaluation Closure Resolver before
evaluation. The resolver verifies root containment, immutable revision, exact content
identity, expected kind/ID, Project compatibility, and acyclicity. It delegates an
explicit Federation Plan edge to the Federation Resolver, which verifies export kind,
project identity, namespace, and child-reference acyclicity; it returns a
normalized closure manifest or stable diagnostics. Absence or mismatch is a diagnostic;
it is not permission to read a working tree default, current time, local locale, or
renderer configuration.

### 5.2 Evaluation pipeline

```text
Load / normalize Project
          ↓
Resolve pinned federated exports (when declared)
          ↓
Validate profiles and semantic structure
          ↓
Resolve temporal values and schedule
          ↓
Build semantic View Projection
          ↓
Resolve Style roles and Theme tokens
          ↓
Build Scene and render target artifact
```

Each stage receives immutable input values and returns a value plus diagnostics. A stage may halt its dependent stages when a required invariant cannot be satisfied, but it must preserve the diagnostics that explain why. It must not repair source data, replace unknown references, or fabricate Actual values.

Federated summary items enter the View Engine as read-only, namespaced projection
inputs. The Scheduling Engine schedules only the parent Project; a published child
interface milestone can satisfy a declared parent dependency boundary but cannot expose
or mutate the child's internal schedule.

### 5.3 Derived-state cache

Derived values MAY be cached. A cache key MUST include the normalized evaluation closure
identity (all revision and content identities, package/engine versions), together with
the explicit render context, viewport, layout metrics, and target capability profile
where relevant.

A cache hit is an optimization only. It must be observationally equivalent to reevaluating the declared inputs and must not hide diagnostics associated with those inputs.

### 5.4 Reactive projection updates

The Runtime Coordinator MUST translate each accepted Command change set into an explicit **impact set** before updating an interactive consumer. The impact set contains the semantic and presentation inputs whose derived results may differ. It is calculated from stable IDs, changed fields, declared dependency edges, View selection/grouping/order rules, Style selectors, Theme token references, and Scene layout constraints.

The coordinator MAY rebuild a larger internal cache when that is cheaper or simpler, but it MUST NOT require the GUI to discard and recreate every rendered node merely because one canonical value changed. It compares the previous and next completed Scenes by `sceneId` and emits the `SceneDelta` defined by [08 Scene and Rendering](08-scene-and-rendering.md).

A whole-Scene `replaceScope` is permitted only when the impact domain is intrinsically global—for example a View/window/scale change, viewport reflow that changes all layout, a Theme or Style rule affecting all nodes, or a scheduling change whose declared dependency closure reaches all displayed objects. It is not an acceptable default for a local field edit. The coordinator supplies the invalidation reason required by the SceneDelta contract so performance tests and diagnostics can distinguish a necessary global invalidation from an accidental full refresh.

### 5.5 Interactive transient state

An interactive client may retain transient local state such as hover, selection, viewport motion, a drag preview, and a pending Command. This state is not canonical and does not require a Project revision.

On an accepted Command, the client reconciles its preview with the matching target `SceneDelta`. On rejection, it removes or corrects only the affected preview and presents diagnostics. When newer evaluation results arrive while an older evaluation is pending, the coordinator or adapter MUST cancel, coalesce, or discard stale work by evaluation identity; stale output must not overwrite a newer completed Scene.

## 6. Mutation flow

```text
CLI / GUI / AI / automation
            ↓
      Command Engine
            ↓
 Project Store transaction
            ↓
New canonical revision + diagnostics
            ↓
Invalidation of derived outputs
```

An interaction such as dragging a bar in a canvas is an input proposal, not a direct coordinate edit. The adapter maps it to an explicit Command request; the Command Engine validates and applies it against canonical state, after which normal evaluation constructs a new Scene.

The same rule applies to AI agents: an agent may inspect diagnostics and request commands, but must not mutate project files, schedule results, SVG, or canvas state outside the Command Engine's declared authorization and validation path.

Concurrent writers require revision-aware conflict handling. A write request MUST name or otherwise bind its base revision, and the Project Store MUST reject or explicitly merge a stale request. Implicit last-writer-wins behavior is prohibited for canonical state.

## 7. Diagnostics and observability

The Runtime Coordinator aggregates diagnostics without changing their owner-defined meaning. A diagnostic envelope SHOULD include:

| Field | Purpose |
|---|---|
| `code` | Stable owner-defined identifier |
| `severity` | Error, warning, or informational level |
| `component` | Producing component |
| `sourceRef` | Relevant semantic, presentation, or command reference |
| `revisionRefs` | Inputs used when it was produced |
| `message` | Human-readable explanation |

Evaluation output SHOULD also expose an input manifest and stage trace sufficient to answer: which revision was rendered, which View/Theme were selected, which cache entry was used, and which component produced each diagnostic. This trace is observational metadata; it must not mutate a Project merely by being collected.

## 8. Adapter and capability boundaries

Renderer adapters declare target capabilities before Scene construction when those capabilities affect required output. The Scene Builder and adapter must diagnose a requested distinction that the target cannot faithfully preserve, such as source metadata, text alternatives, clipping, or marker treatment.

Interactive adapters have two distinct directions:

- **projection:** completed Scene to renderer or canvas state; and
- **interaction translation:** user gesture to an explicit Command proposal.

There is no automatic inverse mapping from arbitrary SVG elements or canvas shapes to Project semantics. Importers, if later added, are separate, lossy ingestion features and require their own specification.

## 9. Current reference implementation

The initial Python implementation provides a Core v0.1 reference validator, Date-only scheduler, CLI, and a small deterministic SVG vertical slice. These modules are useful conformance evidence, but they do not yet constitute the full component architecture described here.

In particular, the existing SVG path does not establish a canonical View, Style, Theme, Scene, cache, editor, or command implementation. New implementation work must be checked against the boundaries in this document and the subsequent Command and Extension specifications.

## 10. Out of scope

This document does not define:

- command names, undo/redo, transaction grammar, or authorization policy;
- service topology, network protocol, database choice, or deployment model;
- a GUI framework, canvas library, graphics library, or tldraw API;
- persistence syntax for Snapshot, Actual, View, Style, Theme, or Scene profiles;
- resource allocation, cost, timesheets, ticket workflows, portfolios, or arbitrary code extensions; or
- DateTime/DST scheduling or automatic rescheduling from Actual observations.

## 11. Boundary to subsequent specifications

[10 Command Model](10-command-model.md) defines the canonical mutation interface used by the Command Engine. [11 Extension Model](11-extension-model.md) defines what the Profile Registry may load and how extensions remain safe and declarative. Application code may add internal modules, but must preserve this document's direction of authority: canonical semantics first, derived presentation second, target adapters last.
