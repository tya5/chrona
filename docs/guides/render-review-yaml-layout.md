# Render-review YAML layout

The current review entry keeps reusable authoring resources separate from the generated
immutable evaluation binding. Users normally edit Project, Actual, View, Preset, and
optional Profile resources. A snapshot/materialization workflow records their immutable
references in a Render Context; `render-review` consumes that Context reference.

## Recommended authoring layout

| Path | Authority | Typical reuse |
|---|---|---|
| `project.yaml` | planned objects, relations, calendars | one project |
| `actual.yaml` | independent observations | one project, independently revised |
| `views/executive.yaml` | selection, grouping, ordering, window | projects sharing the same profile fields |
| `presets/executive.yaml` | Theme, Layout, Detail, locale, viewport, output policy | organization, audience, or medium |
| `profiles/summary.yaml` | bounded summary metrics | many projects |
| `profiles/detail.yaml` | optional group descriptions and review records | shared only when IDs and vocabulary match |

A reusable View avoids object-specific `ids` and selects by types or profile fields.
Project-specific selections belong in a separate named View. A Preset uses a fixed base
plus overrides and does not contain Project facts. A Detail Profile that names group or
object IDs is intentionally project-specific; generic wording and visual treatment
remain in the Preset.

## Generated evaluation binding

`render-context.yaml` contains references, not copies of the authoring resources:

```yaml
version: chrona/presentation/v0.3
kind: render-context
id: controller-z-executive-2026-09-20
body:
  project: {id: controller-z, kind: project, store: {provider: local, identity: review-store}, address: project.yaml, revision: {token: snapshot-42}, contentIdentity: "sha256:..."}
  view: {id: executive-review, kind: view, store: {provider: local, identity: review-store}, address: views/executive.yaml, revision: {token: snapshot-42}, contentIdentity: "sha256:..."}
  presentationPreset: {id: executive, kind: presentation-preset, store: {provider: local, identity: review-store}, address: presets/executive.yaml, revision: {token: snapshot-42}, contentIdentity: "sha256:..."}
  inputs:
    actual: {id: controller-z-observed, kind: actual-set, store: {provider: local, identity: review-store}, address: actual.yaml, revision: {token: snapshot-42}, contentIdentity: "sha256:..."}
  target:
    kind: svg
    capabilities: [accessibleText, hierarchicalAxis, marker, semanticRoles, sourceMetadata, tableSemantics]
```

The Context, every referenced resource, and the CLI's Context-reference document use
the provider-neutral Revision Store reference shape. All resources in one evaluation
use one immutable snapshot token. Content identities are generated evidence, not values
an author should guess or maintain manually.

The alpha CLI currently consumes a pre-materialized local snapshot. It does not yet
claim a snapshot/materialization command. This distinction keeps the public surface
honest while allowing View, Preset, and Profile files to be reused without duplication.
