# Presentation Format

**Status:** Proposed
**Depends on:** [05 Project Format](05-project-format.md), [06 View Model](06-view-model.md), [07 Style and Theme](07-style-and-theme.md), [08 Scene and Rendering](08-scene-and-rendering.md), [10 Command Model](10-command-model.md)
**Owns:** persistent syntax and normalization for View, Style, Theme, Render Context, Scene profile, Snapshot reference, and Actual observation set definitions outside the Core Project file; plus the file-serialization boundary for Command requests.

## 1. Purpose

This document defines the persistent representation boundary for Chrona's Presentation
and Application inputs. It is a companion to the Core-only [05 Project Format](05-project-format.md):
`05` continues to own Project, temporal, scheduling, and Core normalization syntax;
this document owns the separately versioned files that select, compare, and display
that Core data. A serialized Command request is supported as a reviewable or transport
document, but it is not a presentation resource and does not become a member of a
Render Context's resource graph.

The separation prevents a GUI, renderer, or current workspace state from becoming an
implicit extension of `project.yaml` while keeping all authoritative inputs
Git-reviewable.

## 2. Format invariants

- Every persisted presentation definition MUST declare a format version, resource kind, and stable
  resource ID.
- A definition MUST reference every Project, Snapshot, Actual, Style, Theme, Scene
  profile, and Render Context input it needs by explicit ID or immutable reference.
- A consumer MUST NOT select a local file, Git branch, current date, installed theme, or
  renderer default as an unstated input.
- Every input to an evaluation MUST be bound to an immutable revision and exact content
  identity; a path is a locator, never an identity.
- Scene, SVG, canvas state, layout caches, and generated deltas MUST NOT be persisted as
  authoritative inputs to this format.
- Canonicalization MUST preserve stable IDs, normalize unordered maps deterministically,
  and avoid rewriting unrelated resources.

## 3. Resource envelope

Every resource uses a common YAML envelope. The resource-specific body is validated by
the schema for its `kind`.

```yaml
version: chrona/presentation/v0.1
kind: view
id: controller-review
body: {}
```

The initial kinds are:

| Kind | Owner specification | Purpose |
|---|---|---|
| `view` | View Model | Selection, grouping, comparison inputs, visibility, and layout intent |
| `style` | Style and Theme | Declarative semantic selectors and visual-role assignment |
| `theme` | Style and Theme | Concrete named token values and declared variants |
| `render-context` | Application Architecture | Explicit active resources and environment values for one evaluation |
| `scene-profile` | Scene and Rendering | Temporal scale, lane layout, routing, collision, and layout-metric policy |
| `snapshot-ref` | View Model | Immutable named Project comparison reference |
| `actual-set` | View/Command Model | Independently observed Actual observations and explicit alignment state |

`kind` is not an extension point by itself. New resource kinds require an owning
specification and a versioned schema; unknown kinds may be preserved losslessly but
MUST NOT be interpreted.

A Command request has the conceptual envelope and `commandId` owned by the
[Command Model](10-command-model.md). It may be serialized as YAML or JSON for CLI,
AI, review, or fixture use, but it is evaluated as an input request—not loaded by a
Render Context, assigned a resource `id`, or treated as canonical state. Its transport
schema may reuse common scalar and reference definitions from this format without
changing Command Model semantics.

## 4. Repository composition

The initial multi-file layout is explicit rather than include-driven:

```text
project.yaml
views/<view-id>.yaml
styles/<style-id>.yaml
themes/<theme-id>.yaml
contexts/<context-id>.yaml
scenes/<scene-profile-id>.yaml
snapshots/<snapshot-id>.yaml
actuals/<actual-set-id>.yaml
```

A Render Context is the entry point for a presentation evaluation. It names the
resources used for a single evaluation, including the primary Project revision and any
Snapshot or Actual input. Each resource reference includes its expected stable ID, kind,
canonical repository-relative path, immutable revision, and content identity. A loader
verifies all five values; it does not search a directory to find a matching ID.
Duplicate `(kind, id)` pairs in an evaluation are invalid.

Multiple Render Contexts MAY refer to the same immutable Project revision. They remain
independent evaluations: one Context's View selection, Theme, Actual input, viewport,
or cache identity MUST NOT become an unstated default for another Context. A
multi-context conformance fixture must demonstrate this isolation using named contexts.

Recursive includes, glob imports, implicit directory scans, and merge-by-file-order are
outside v0.1 of this format. They must not be inferred by an implementation.

## 5. Reference semantics

References are typed and explicit. A reference is normalized before use to the following
shape. `path` is normalized from the declared repository root using `/`, MUST NOT contain
`.` or `..` segments, and MUST resolve inside that root. `revision` identifies the
immutable source tree; v0.1 accepts only a full Git object ID (`git:` followed by 40 or
64 hexadecimal characters). `contentIdentity` is the SHA-256 of the exact UTF-8 bytes
loaded at that path. It protects evaluation reproducibility even when a Git backend is
unavailable after materializing a verified closure.

```yaml
id: controller-x
kind: project
path: timeline-design/docs/fixtures/controller-x.yaml
revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df
contentIdentity: sha256:8e3a8360736368ca36d09eca8ca7fc473bfdcd902d3a214d85d560521a7425db
```

The expected `kind` and `id` are mandatory even for a Project reference. A Project
reference's ID MUST equal the resolved `project.id`; a presentation reference's ID and
kind MUST equal the resolved envelope. The identity check precedes owner-semantic
evaluation.

### 5.1 Evaluation closure and resolution

An **evaluation closure** is the ordered, immutable set of resources consumed by one
Render Context: Render Context; primary Project; View; Style; Theme; Scene Profile;
the selected Snapshot and Actual set, if any; declared extension packages; and the
layout-metrics artifact. When the evaluation names a Federation Plan, the
closure also contains each resolved child `timeline-export` in deterministic parent
reference order. The normalized closure manifest records each resource's
`kind`, `id`, canonical `path`, `revision`, and `contentIdentity`, plus the engine and
package-registry versions used to resolve it.

Resolution MUST:

1. normalize every path against the repository root and reject escape;
2. read the named content from the named immutable revision, never from a moving branch
   or the current working tree;
3. verify SHA-256, envelope kind/ID, Project ID, and supported version;
4. recursively resolve declared resource/package edges in deterministic field order;
5. reject a cycle, duplicate `(kind, id)` with different identities, missing object,
   unavailable revision, or a Snapshot/Actual whose Project ID differs from the primary
   Project; and
6. emit the normalized closure as evaluation evidence before scheduling or rendering.

A federation edge is resolved only from an explicit typed, pinned Federation Plan export
reference. The resolver verifies the export's repository locator, kind, declared child
Project ID, immutable revision, content identity, and federation namespace; it rejects a child branch tip,
raw child Project input, or duplicate namespace. Federation v0.1 exports cannot contain
federation edges, so a cycle is structurally unrepresentable. Child exports
are read-only projection inputs, not extra primary Projects or hidden mutable context.

An editor may use a separately persisted immutable Project-Store object while offline,
but it MUST assign a content identity and materialize the same closure manifest before
the result is comparable or cacheable. `git:main`, abbreviated Git IDs, filesystem
mtime, and "latest" are invalid in a reproducible closure.

The layout-metrics artifact follows the same rule. Its `id`, revision, content identity,
metric algorithm version, and declared font/metric payload are part of the closure; an
installed font or host default is never a substitute.

### 5.2 Reference examples

A Project/Snapshot reference identifies both a logical source and its immutable
revision:

```yaml
body:
  project: {id: controller-x, kind: project, path: project.yaml, revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df, contentIdentity: sha256:8e3a8360736368ca36d09eca8ca7fc473bfdcd902d3a214d85d560521a7425db}
```

For an editable working evaluation, `revision` MAY be a project-store revision ID rather
than a Git commit, but it MUST be recorded in the evaluation manifest. A reference to a
moving branch name, such as `main`, is invalid as a reproducible comparison input.

A presentation-resource reference uses an expected kind, ID, path, revision, and
content identity. For example:

```yaml
body:
  view: {id: controller-review, kind: view, path: views/controller-review.yaml, revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df, contentIdentity: sha256:fa9890a9b332ec65bca410a9251ba609eceff5ac494c3110dc20d5200d4c4e9c}
```

The canonical path is resolved from the declared repository root. A file with the right
path but a different revision, content identity, kind, or ID is invalid. This explicit
pairing keeps an ID rename or a path move reviewable and avoids an unstated registry or
filesystem scan.

An Actual observation may have a resolved `projectObjectId` or an external identity with
`alignment: unmatched`. Text similarity is never a normalization or alignment rule.

### 5.3 Render Context v0.1 body

A `render-context` selects exactly one immutable primary Project revision and exactly
one View, Style, Theme, and Scene profile. It supplies the concrete comparison inputs
declared by that View, plus the environment values that can affect a completed Scene.
The View owns whether a Snapshot or Actual input is meaningful or required; the Render
Context owns which explicitly named instance is used for this evaluation.

```yaml
version: chrona/presentation/v0.1
kind: render-context
id: controller-plan-vs-actual
body:
  project: {id: controller-x, kind: project, path: project.yaml, revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df, contentIdentity: sha256:8e3a8360736368ca36d09eca8ca7fc473bfdcd902d3a214d85d560521a7425db}
  view: {id: controller-review, kind: view, path: views/controller-review.yaml, revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df, contentIdentity: sha256:fa9890a9b332ec65bca410a9251ba609eceff5ac494c3110dc20d5200d4c4e9c}
  style:
    id: plan-actual
    path: ../styles/plan-actual.yaml
  theme:
    id: engineering-light
    path: ../themes/engineering-light.yaml
  sceneProfile:
    id: date-lanes
    path: ../scenes/date-lanes.yaml
  inputs:
    snapshot:
      id: baseline-q2
      path: ../snapshots/baseline-q2.yaml
    actual:
      id: controller-observed
      path: ../actuals/controller-observed.yaml
  evaluation:
    locale: ja-JP
    asOfDate: 2026-09-17
  viewport:
    width: 1600
    height: 900
    margins: { top: 32, right: 48, bottom: 40, left: 160 }
    clipping: clip
  target:
    kind: svg
    capabilities: [metadata, marker, text-alternative]
  layoutMetrics: {id: inter-14-logical, revision: metric:inter-14-v1, contentIdentity: sha256:0000000000000000000000000000000000000000000000000000000000000000, algorithmVersion: chrona-layout-metrics/v0.1}
```

`inputs.snapshot`, `inputs.actual`, and `evaluation.asOfDate` are optional only when
the selected View and Scene profile do not require them. Omission must remain visible in
the input manifest; it never means “use the latest Snapshot”, “read the local clock”,
or “infer a default Actual set”. `locale`, `viewport`, `target`, and `layoutMetrics`
are required for a renderable Scene in v0.1. The `layoutMetrics` revision identifies a
declared metrics dataset or algorithm profile; its acquisition and payload format remain
outside this document, but a renderer must not substitute installed-font metrics.

The `target.capabilities` list is a sorted, duplicate-free declaration. A Scene Builder
uses it to diagnose distinctions the requested output cannot preserve; it does not use
the target `kind` to infer unrecorded defaults. No target-specific options belong in a
Render Context until a target-capability specification defines their portable meaning.

## 6. Normalization and validation sequence

The loader evaluates resources in this order:

```text
Evaluation closure resolution
  ↓
YAML syntax
  ↓
Common presentation envelope
  ↓
Kind-specific schema
  ↓
Typed resource references
  ↓
Owner-specification semantics
  ↓
Evaluation manifest and derived Scene
```

### 6.1 Snapshot and Actual v0.1 design

A `snapshot-ref` names an immutable Project input and adds no copied schedule data:

```yaml
kind: snapshot-ref
id: baseline-q2
body:
  project: {id: controller-x, kind: project, path: project.yaml, revision: git:8de5f81481b0ad44b4532d3a485f5aee92fdd4df, contentIdentity: sha256:8e3a8360736368ca36d09eca8ca7fc473bfdcd902d3a214d85d560521a7425db}
```

An `actual-set` is an independently revisioned observation collection. Each observation
has a stable observation ID and either a resolved `projectObjectId` or an external
identity marked `alignment: unmatched`. Date values use the existing Date-only domain;
progress, when present, is a decimal fraction in `[0, 1]`.

```yaml
kind: actual-set
id: controller-observed
body:
  observations:
    - id: observed-firmware
      projectObjectId: firmware
      actual: {start: 2026-04-03, finish: 2026-04-18, progress: 0.75}
    - id: imported-42
      externalIdentity: {system: supplier, key: 42}
      alignment: unmatched
      actual: {finish: 2026-04-20}
```

An observation MAY be partial. Missing planned/actual endpoints produce a declared
comparison facet or diagnostic, never an invented value. Actual-set edits invalidate
only comparison facets and their downstream Scene primitives unless a View selection or
layout rule explicitly depends on that facet. They never mutate the Project, Snapshot,
or derived planned schedule.

The loader reports unknown kind, duplicate resource ID, unresolved reference,
incompatible version, invalid external path, and owner-semantic diagnostics without
inventing defaults. Presentation-resource references must form an acyclic graph.
Command undo references are evaluated under the Command Model and are not edges in this
resource graph.

## 7. Boundary to schemas and fixtures

This document establishes the common envelope and resource graph. Before an
implementation is conforming, the repository must add:

- one schema per initial resource kind;
- a minimal render-context fixture using one Project, View, Style, Theme, and Scene
  profile;
- Snapshot/Actual alignment and unmatched-observation fixtures;
- Command accept/reject and base-revision fixtures; and
- `SceneDelta` fixtures that demonstrate a local change without unrelated node
  recreation and a declared global invalidation case.

Exact body fields for each kind belong to the owning specification and are introduced
with its schema and canonical fixture. They must not be invented by a renderer or GUI.

The schema sequence is deliberately dependency-ordered: common presentation envelope
and typed-reference definitions; Render Context; View; Style and Theme; Scene profile;
then Snapshot and Actual set. Command request fixtures use the Command Model envelope
and validate any shared reference scalar separately. This prevents a command transport
choice from becoming a hidden dependency of rendering or persistence.

## 8. Schema handoff inventory

The first schema and fixture tranche is intentionally structural. It proves that every
evaluation input is explicit without prematurely freezing the selector, token, or layout
languages still owned by the presentation specifications.

| Schema / fixture | Defined here | Owner-semantic handoff required before conformance |
|---|---|---|
| Common presentation envelope | `version`, `kind`, `id`, `body`, and closed top-level fields | Resource-specific `body` meaning |
| Typed presentation reference | expected kind, stable `id`, repository-relative `path` | Whether the referenced resource is optional, repeatable, or precedence-bearing |
| Render Context | primary Project immutable reference; explicit View, Style, Theme, Scene-profile, Snapshot, Actual, viewport, and capability references | Required-versus-optional inputs and evaluation semantics from Application Architecture |
| View | envelope and declared comparison-input references | Selection, grouping, ordering, window, and annotation language from View Model |
| Style / Theme | envelope and declared parent/variant/reference form | Selector precedence, visual roles, token inheritance, and token value vocabulary from Style and Theme |
| Scene profile | envelope and layout-metric/capability references | Scale, lane, routing, collision, and layout policy from Scene and Rendering |
| Snapshot reference / Actual set | immutable Project reference; resolved or explicitly unmatched Actual alignment identity | Capture semantics and Actual observation fields from View and Command Model |
| Command request document | command envelope, target, and base-revision scalar shapes | Command type/payload vocabulary, transaction, and undo semantics from Command Model |

Canonical fixtures follow the same order. A fixture validates structural syntax first,
then asserts the diagnostic or projection behavior supplied by its owning specification.
For example, the first Render Context fixture must name exact paths and revisions but
does not itself define how a View selector ranks objects; that remains a View Model
fixture once the selector language is specified.

## 8.1 Deferred semantic-format decisions

Before schemas are promoted from structural validation to conformance, these owning
documents must settle their remaining body languages in dependency order:

1. Scene profile: Date lane extent, label collision diagnostics, routing constraints,
   and metric-profile identity;
2. Snapshot reference: immutable capture identity and Project compatibility checks;
3. Actual set: observation fields, progress representation, and alignment diagnostics;
4. Command request serialization: command-type registry and transaction document form.

None may be inferred from a renderer, current Git branch, file order, or GUI state.
This is deliberately a design gate: adding a permissive schema or fixture before these
meanings are settled would make an accidental implementation choice appear normative.

The Command Model has now settled its request-document boundary. It is deliberately
excluded from the presentation resource envelope and Render Context composition; only
its typed target references may share scalar syntax with this format.

## 9. Out of scope

This document does not define package acquisition, remote fetching, authentication,
Git merge strategy, GUI/editor state persistence, command authorization, or arbitrary
code execution. It also does not alter the Core v0.1 Project Format or make generated
Scene state canonical.
