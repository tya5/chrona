# Federated Projects Design

**Status:** Draft  
**Purpose:** Allow a program Project to render approved timelines from independently
owned subprojects without making their source files shared mutable state.

## Decision

Chrona uses **federated immutable exports**, not parent-owned child editing, recursive
file inclusion, or a moving Git branch reference. A child Project remains authoritative
in its repository. It publishes a small timeline export containing its Project identity,
export identity, selected public summary objects/relations, and immutable revision and
content identity. The parent stores a typed, pinned reference to that export.

This follows Git's useful separation of commits for subprojects while avoiding a
submodule checkout as an implicit evaluation input. Git submodules keep nested commits
separate, but Chrona needs a semantic export contract rather than a source-tree mount.

## Federation reference

```yaml
federatedProjects:
  - id: firmware
    export: {projectId: firmware, repository: git+https://host.example/org/firmware.git, path: exports/program.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
    presentation: {mode: summary, namespace: firmware}
```

The normalized reference additionally declares a canonical `repository` locator (for
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
- Cyclic federation references and unpinned/stale branch names are invalid.

## Export boundary

The export is a separate, versioned resource, not a filtered raw Project file. Its
minimum future envelope must name `kind: timeline-export`, export ID, child Project ID,
exported summary object IDs and kinds, published interface milestones, declared progress
aggregation rule, and source revision/content identity. A child may publish no internal
dependencies or private objects. The parent must diagnose a requested non-published
object instead of attempting to discover it in child source.

## Required follow-up evidence

The Project Format, Presentation closure resolver, schemas, and fixtures must add
federation-reference structural and semantic validation before UC-14 is promoted from
design to implementation-ready.
