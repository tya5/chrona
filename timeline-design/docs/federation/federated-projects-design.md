# Federated Projects Design

**Status:** Draft  
**Purpose:** Allow a program Project to render approved timelines from independently
owned subprojects without making their source files shared mutable state.

## Decision

Chrona uses **federated immutable exports**, not parent-owned child editing, recursive
file inclusion, or a moving Git branch reference. A child Project remains authoritative
in its repository. It publishes a small timeline export containing its Project identity,
export identity, selected public summary objects/relations, and immutable revision and
content identity. The parent repository stores a typed, pinned reference to that export
in a separately versioned Federation Plan.

This follows Git's useful separation of commits for subprojects while avoiding a
submodule checkout as an implicit evaluation input. Git submodules keep nested commits
separate, but Chrona needs a semantic export contract rather than a source-tree mount.

## Resources and federation reference

Federation is deliberately outside `timeline/v0.1` Project syntax. That schema rejects
unknown top-level fields, and silently relaxing it would break v0.1 validation. The
first federation capability instead has two explicit resources:

- child `chrona/timeline-export/v0.1`, which exposes an approved public interface; and
- parent `chrona/federation-plan/v0.1`, which names its primary Project plus pinned
  child exports.

The plan is canonical parent-side configuration, but it is not a second Project and it
does not merge child objects into the primary Project. A future Presentation-format
minor version will add the typed Federation Plan reference to a Render Context; v0.1
Render Contexts remain unchanged and cannot claim federation support.

```yaml
version: chrona/federation-plan/v0.1
id: program-federation
primaryProject: {id: program, kind: project, path: project.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
exports:
  - id: firmware
    export: {id: firmware-program, kind: timeline-export, projectId: firmware, repository: git+https://host.example/org/firmware.git, path: exports/program.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
    presentation: {mode: summary, namespace: firmware}
```

The normalized export reference additionally declares a canonical `repository` locator (for
example, `git+https://host/org/firmware.git`); the repository locator, `projectId`,
path, revision, and content identity are verified before evaluation. A locator is not
itself trust: an implementation accepts it only through a separately configured trust
policy.

Child object IDs are namespaced as `federation-id:child-object-id`; parent and child data are
never merged into one canonical Project document. Parent-owned dependencies may target a
declared child **published interface milestone** only. They do not rewrite or schedule
inside the child; a failed/missing interface emits a federation diagnostic.

## Boundaries

- Child leaders mutate their own Project only through their own Command target.
- The parent mutates only its federation reference and parent-owned milestones.
- A parent View may select child summary items; Style/Theme/Scene treat them as derived
  projection inputs.
- Aggregated progress is display-only and declares its aggregation rule; it is never
  written back into a child or used as a scheduling input.
- Federation v0.1 is one-way (Plan → Export) and an Export has no federation edge;
  cycles are structurally unrepresentable. Unpinned/stale branch names are invalid.

## Export boundary and trust

The export is a separate, versioned resource, not a filtered raw Project file. Its
envelope names `kind: timeline-export`, export ID, child Project identity, exported
summary object IDs and kinds, published interface milestones, declared progress
aggregation rule, and source revision/content identity. A child may publish no internal
dependencies or private objects. The parent must diagnose a requested non-published
object instead of attempting to discover it in child source.

Trust is allow-list based: a resolver accepts a `repository` only when it matches a
configured repository identity and the resolved revision/content identity match. A
missing, untrusted, incompatible, unavailable, cyclic, or stale reference produces a
stable diagnostic. It never falls back to a locally checked-out repository or a branch
tip.

## Parent mutation

Federation Plan mutation uses the closed `chrona/federation-command/v0.1` registry:
`pinFederatedExport` replaces one named export reference after validating the exact
export; `unpinFederatedExport` removes one named reference after checking that no
parent-owned interface declaration still targets it. Both target only the Federation
Plan and require its base revision. They cannot send a Command to a child Project,
modify an export, or mutate child schedules.

## Required follow-up evidence

The Presentation closure resolver, future Render Context minor version, schemas, and
fixtures must add federation-plan structural and semantic validation before UC-14 is
promoted from design to implementation-ready.
