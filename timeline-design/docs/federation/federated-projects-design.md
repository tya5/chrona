# Federated Projects Design

**Status:** Proposed
**Purpose:** Allow a program Project to render approved timelines from independently
owned subprojects without making their source files shared mutable state.

## Decision

Chrona uses **federated immutable exports**, not parent-owned child editing, recursive
file inclusion, or a moving source selector. A child Project remains authoritative
in its own Revision Store. It publishes a small timeline export containing its Project identity,
export identity, selected public summary objects/relations, and immutable revision and
content identity. The parent repository stores a typed, pinned reference to that export
in a separately versioned Federation Plan.

Git's separation of commits is one useful implementation of this rule, but it is not
required. Chrona needs a semantic export contract rather than a shared source-tree
mount. The provider-neutral persistence boundary is owned by
[Revision Store Adapters](../specification/15-revision-store-adapters.md).

## Resources and federation reference

Federation is deliberately outside `timeline/v0.1` Project syntax. That schema rejects
unknown top-level fields, and silently relaxing it would break v0.1 validation. The
first federation capability instead has two explicit resources:

- child `chrona/timeline-export/v0.1`, which exposes an approved public interface; and
- parent `chrona/federation-plan/v0.1`, which names its primary Project plus pinned
  child exports.

The plan is canonical parent-side configuration, but it is not a second Project and it
does not merge child objects into the primary Project. `chrona/presentation/v0.2` adds
one required typed `federationPlan` reference to a Render Context. v0.1 Render Contexts
remain unchanged and cannot claim federation support.

The resolver first verifies the Federation Plan, then resolves only the export
references recorded in that Plan revision. A newer child export, child branch tip, or
working-tree file is not an evaluation input. A child change is therefore invisible
until `pinFederatedExport` creates a new Plan revision and v0.2 names that revision.

The conformance fixtures `closure-before-repin.yaml` and `closure-after-repin.yaml`
make this rule executable: they expose both child revisions, assert that the old Plan
selects only the old export, then assert that a repinned Plan selects the new export.

```yaml
version: chrona/federation-plan/v0.1
id: program-federation
primaryProject: {id: program, kind: project, path: project.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
exports:
  - id: firmware
    export: {id: firmware-program, kind: timeline-export, projectId: firmware, repository: git+https://host.example/org/firmware.git, path: exports/program.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
    presentation: {mode: summary, namespace: firmware}
```

The v0.1 example is Git-adapter-only. `chrona/federation-plan/v0.2` is its
provider-neutral successor. It reuses the resource-reference contract from
[15 Revision Store Adapters](../specification/15-revision-store-adapters.md): every
primary-Project and child-export reference declares a Store/provider identity, normalized
Address, store-owned revision token, and content identity. The child export additionally
declares its `projectId`.

```yaml
version: chrona/federation-plan/v0.2
id: program-federation
primaryProject:
  id: program
  kind: project
  store: {provider: local, identity: workstation-programs, locator: chrona://programs}
  address: projects/program.yaml
  revision: {token: snapshot:2026-09-18T15:00:00Z:81ab}
  contentIdentity: sha256:<64-hex>
exports:
  - id: firmware
    export:
      id: firmware-program
      kind: timeline-export
      projectId: firmware
      store: {provider: content, identity: firmware-release-key-1, locator: pkg://firmware/v4}
      address: exports/program.yaml
      revision: {token: sha256:<64-hex>}
      contentIdentity: sha256:<64-hex>
    presentation: {mode: summary, namespace: firmware}
```

A locator is not itself trust: an implementation accepts a resource only through
separately configured trust policy for the adapter/provider and source identity. It then
verifies the pinned token and content identity. The core never compares tokens from two
Stores, nor does it infer trust from an URL, local filesystem path, or package name.

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

Trust is allow-list based: a resolver accepts a source only when its declared Store
provider and identity match configured policy (for example a Git repository identity,
local-store namespace, or package signer) and the resolved token/content identity match.
A missing, untrusted, incompatible, unavailable, cyclic, or stale reference produces a
stable diagnostic. It never falls back to a locally checked-out repository, local Draft,
branch tip, or database "latest" value.

## Parent mutation

Federation Plan mutation uses the closed `chrona/federation-command/v0.1` registry for
legacy Git-shaped documents and a successor command envelope for v0.2 references:
`pinFederatedExport` replaces one named export reference after validating the exact
export; `unpinFederatedExport` removes one named reference after checking that no
parent-owned interface declaration still targets it. Both target only the Federation
Plan and require its target Store's opaque base-revision token. They cannot send a
Command to a child Project, modify an export, or mutate child schedules. Pinning never
follows a new child version; it writes one new immutable parent Plan Snapshot that names
the selected child Snapshot explicitly.

## Required follow-up evidence

RA-5 supplies the v0.2 schema and Git/local/content fixtures. The Presentation closure
resolver must validate this provider-neutral Plan before UC-14 is promoted from design
to implementation-ready.
