# Application Architecture

**Status:** Proposed
**Depends on:** Core Specification (`01`–`05`), Presentation Specification (`06`–`08`), [15 Revision Store Adapters](15-revision-store-adapters.md)
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
| Revision Store adapter | Resolve immutable snapshots, read resources, and optionally persist canonical changes | Temporal interpretation, scheduling, or rendering |
| Evaluation Closure Resolver | Resolve and verify the immutable resource/package closure named by a Render Context | Fallback to current files, branches, or host defaults |
| Federation Resolver | Resolve pinned child timeline exports and compose read-only summary inputs | Loading a child branch tip, editing child data, or treating a raw child Project as a parent resource |
| Profile Registry | Resolve supported core and extension profiles, typed fields, and schemas | Arbitrary executable extension behavior |
| Temporal Engine | Parse and operate on temporal values and calendars | Project mutation policy or visual layout |
| Scheduling Engine | Validate and derive planned placements under the Scheduling Model | Actual-driven rescheduling or presentation decisions |
| Transform / Predicate Engine | Evaluate declarative selection, grouping, ordering, and comparison predicates | Host-language expression execution or geometry |
| View Engine | Build a semantic View Projection from explicit state and View Context | Colours, fonts, primitive coordinates, or project mutation |
| Style Resolver | Resolve semantic selectors to visual roles | Scheduling, geometry, or literal token values |
| Theme Resolver | Resolve role token references to concrete visual values | Semantic selection or role conditions |
| Scene Builder | Build one ResolvedPresentationInput, then produce positioned, metadata-preserving Scene primitives | Semantic source data or renderer-owned layout conventions |
| Renderer Adapter | Translate a completed Scene to SVG, canvas, or another declared target | Semantic inference or canonical state mutation |
| Command Engine | Apply validated semantic or presentation-definition mutations as new revisions | Renderer-specific interaction behavior or scheduling semantics |
| Runtime Coordinator | Bind explicit inputs, invoke components in dependency order, collect diagnostics, and manage derived caches | Hidden policy changes or alternate semantic rules |

The Command Engine's command vocabulary, transactions, undo/redo, and mutation result semantics belong to [10 Command Model](10-command-model.md). This document only defines its placement and integration boundary.

### 3.2 Dependency direction

```text
Revision Store resource references
                ↓
Revision Store adapter ──→ Profile Registry
        │                 │
        └──────→ Temporal Engine
                         ↓
                   Scheduling Engine
                         ↓
 Transform / Predicate → View → Style → Theme → Scene → Renderer adapters

CLI / GUI / AI / automation → Command Engine → Revision Store adapter
```

Dependencies point toward lower-level semantics and then outward toward presentation. A renderer adapter must never depend on a Revision Store adapter to infer missing data, and the Scheduling Engine must never depend on a View, Theme, Scene, or renderer.

## 4. State ownership and persistence boundaries

| State category | Authoritative owner | Persistence rule |
|---|---|---|
| Project, profiles, calendars, semantic annotations, and relations | Revision Store | Canonical, reviewable structured source data in one immutable snapshot |
| Named Snapshot and Actual input references | Their specified persistence model | Explicitly named, immutable or independently observed input; never inferred as “latest” |
| Federation Plan and child export | Parent plan / child Revision Store | Immutable, read-only export consumed through a parent-owned pinned plan reference; never merged into parent canonical data |
| View, Style, Theme, and Scene-profile definitions | Their respective specifications | Declarative versioned data; serialization syntax may evolve independently |
| Schedule result, View Projection, resolved Style/Theme, Scene, SVG, canvas store | Runtime Coordinator / adapters | Derived cache or output only; invalidated when any declared input changes |
| Diagnostics, manifests, and trace data | Runtime Coordinator | Inspectable output; not a substitute for canonical source |

The Revision Store resolves a Snapshot identity for every reproducible load and returns a
new Snapshot for an accepted write. Evaluation and rendering requests bind that identity,
so a schedule, View Projection, and Scene from different Project revisions cannot be
combined accidentally. A raw editable file is a Draft until the Store snapshots it.

### 4.1 CLI read modes

CLI read commands expose the authority boundary rather than hiding it. A caller chooses
either a raw Project path, which is reported and documented as Draft evaluation, or a
complete local snapshot tuple consisting of a snapshot-reference resource, adapter
root, and store identity. Snapshot mode calls the same `LocalSnapshotReader` and loader
used by library evaluation and never falls back to the raw path when reference
resolution fails.

Presentation output similarly chooses either resolved Presentation Settings and the
common Scene path, or the explicit diagnostic legacy adapter. `render-review` accepts
only an immutable Render Context v0.3 reference plus its declared Store; it does not
reconstruct a context from loose Project/Actual/View/Style/Theme/Profile flags. A CLI
must not infer a Render Context from host fonts, locale, or canvas defaults.

The reproducible `review` verb accepts two immutable Project references in one declared
Store. Raw paths are Draft evaluation inputs for `validate`, `schedule`, and minimal
`render`; they are not a reproducible revision comparison.

## 5. Read evaluation flow

### 5.1 Evaluation request

Every read evaluation begins with an explicit request containing at least:

- a current Render Context that names the primary Project revision, View, resolved
  Presentation Settings, and named Snapshot/Actual/detail inputs when used;
- its explicit target capabilities; locale, viewport, layout, Theme, Detail, font
  metrics, and output policy are closed by the referenced Presentation Settings; and
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
Resolve the declared v0.1 Style/Theme stack or current v0.2 Presentation Settings
          ↓
Build Scene and render target artifact
```

Each stage receives immutable input values and returns a value plus diagnostics. A stage may halt its dependent stages when a required invariant cannot be satisfied, but it must preserve the diagnostics that explain why. It must not repair source data, replace unknown references, or fabricate Actual values.

Before Scene construction, the Runtime Coordinator binds the View Projection, resolved
Style/Theme, Detail, Layout, metrics, viewport, and target capabilities into the
single ResolvedPresentationInput defined by specification 08.  This is the only
authoring-to-geometry boundary.  The Scene Builder owns its derived projection
instances and primitive identities; Renderer Adapters receive only the completed
Scene and may serialize it without semantic or geometric re-evaluation.

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

The Runtime Coordinator aggregates diagnostics without changing their owner-defined
meaning. Every CLI failure MUST emit one JSON object with `status` and a `diagnostics`
array. Each diagnostic uses this envelope:

| Field | Purpose |
|---|---|
| `code` | Stable owner-defined identifier |
| `severity` | Error, warning, or informational level |
| `component` | Producing component |
| `sourceRef` | Relevant semantic, presentation, or command reference |
| `revisionRefs` | Inputs used when it was produced; empty when the failure precedes resolution |
| `message` | Human-readable explanation |

Project or presentation rejection returns process status 1. Invalid command syntax,
unreadable input, malformed YAML/JSON, or an internal tooling failure returns 2. A
handled failure never emits a Python traceback. Successful commands return 0.

Evaluation output SHOULD also expose an input manifest and stage trace sufficient to answer: which revision was rendered, which View/Theme were selected, which cache entry was used, and which component produced each diagnostic. This trace is observational metadata; it must not mutate a Project merely by being collected.

## 8. Adapter and capability boundaries

Renderer adapters declare target capabilities before Scene construction when those capabilities affect required output. The Scene Builder and adapter must diagnose a requested distinction that the target cannot faithfully preserve, such as source metadata, text alternatives, clipping, or marker treatment.

Interactive adapters have two distinct directions:

- **projection:** completed Scene to renderer or canvas state; and
- **interaction translation:** user gesture to an explicit Command proposal.

There is no automatic inverse mapping from arbitrary SVG elements or canvas shapes to Project semantics. Importers, if later added, are separate, lossy ingestion features and require their own specification.

## 9. Current reference implementation

The Python implementation provides the Core v0.1 validator and scheduler, immutable
local Revision Store reads, typed Commands, View/Actual projection, resolved
Presentation Settings, a renderer-neutral Scene, deterministic SVG adapters, and
library implementations of the successor capabilities. The `chrona` CLI is a smaller
product surface; Specification 14 records that reachability separately from library
evidence. No library module is user-reachable merely because it has tests.

## 10. Collaboration successor integration

The Collaboration Coordinator is an application adapter between authenticated clients
and the Command/Revision Store boundaries. It may synchronize snapshots, request an
authorization/approval decision, present conflict objects, and append audit evidence.
It must not edit Project bytes, select a merge winner, or derive schedule/Scene state.
An approval is checked against the exact command fingerprint and current policy before
Command persistence; a changed payload or base revision requires a new approval.

## 11. Extension lifecycle successor integration

The Profile Registry resolves only the explicit declarative package closure verified by
the Evaluation Closure Resolver. It reports lifecycle/compatibility diagnostics and
passes typed profiles to Core validation. A host Plugin Manager installs code plugins
under separate host policy and API compatibility checks; it cannot inject a package,
override profile semantics, or mutate canonical state except through Command.

## 12. Out of scope

This document does not define:

- command names, undo/redo, transaction grammar, or authorization policy;
- service topology, network protocol, database choice, or deployment model;
- a GUI framework, canvas library, graphics library, or tldraw API;
- persistence syntax for Snapshot, Actual, View, Style, Theme, or Scene profiles;
- resource allocation, cost, timesheets, ticket workflows, portfolios, or arbitrary code extensions; or
- DateTime/DST scheduling or automatic rescheduling from Actual observations.

## 13. Boundary to subsequent specifications

[10 Command Model](10-command-model.md) defines the canonical mutation interface used by the Command Engine. [11 Extension Model](11-extension-model.md) defines what the Profile Registry may load and how extensions remain safe and declarative. Application code may add internal modules, but must preserve this document's direction of authority: canonical semantics first, derived presentation second, target adapters last.
