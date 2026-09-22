# Issue 136 Scenario Overlays: Design and Architecture Review

## Decision

A Scenario is a named, Project-owned hypothesis over the current Project.  It
is resolved to an ephemeral derived Project before the unchanged scheduler
runs, then participates in the existing comparison projection under source
kind `scenario`.  It is neither a Snapshot nor a second Project resource, and
it is never persisted as Scene, Layout, or renderer state.

The successor contracts are **Project v0.5** and **View v0.7**.  This is an
intentional clean cut: v0.4/v0.6 are not accepted as aliases by the new
contracts.  All materializable public resources and compatible Profile package
requirements migrate atomically in the implementation contract slice.

## Ownership and boundary review

| Concern | Owner | Explicit non-owner |
|---|---|---|
| Scenario declaration, frame restriction, recursive merge law | Project Format | View, scheduler, Scene |
| Resolve scenario id to an ephemeral Project value | Application/closure resolver | renderer, Layout |
| Placement and dependency validity of the derived value | Existing Scheduler | scenario merger |
| Automatic baseline and explicit row source selection | View Model | Project, Layout |
| Scenario identity/title as table and summary facts | View projection/content normalization | Scene, renderer |
| Geometry and routing | Layout | scenario resolver |
| Primitive projection and SVG serialization | Scene / renderer | scenario semantics |
| Determinism, provenance, diagnostics, non-mutation | Quality and Invariants | ad hoc adapters |

This preserves the established pipeline:

```text
Project v0.5 + scenario id ──resolve──> derived Project ──schedule──> placements
       │                                                              │
       └────────────── primary Project ──schedule──> placements       │
                              │                                        │
                              └──────────── View v0.7 ──> Projection ──> Layout → Scene → Renderer
```

No branch in that graph permits a Scenario to change a primary placement,
Actual observation, Snapshot, Layout placement, or renderer rule.

## Persistent Project contract

`timeline/v0.5` adds an optional top-level `scenarios` mapping.  A key is a
stable scenario id.  Each value has an optional human title, object overrides,
and relation operations:

```yaml
scenarios:
  tvac-slip:
    title: TVAC slips three weeks
    objects:
      tvac:
        schedule: {amount: 21d}
      contingency-task:
        type: task
        title: Contingency thermal test
        schedule: {mode: scheduled, amount: 5wd}
    relations:
      remove: [tvac-to-launch]
      add:
        - {id: contingency-to-launch, type: dependency,
           from: {object: contingency-task, endpoint: end},
           to: {object: launch, endpoint: start}}
```

`objects.<id>: null` removes an existing object.  A mapping for an existing
object merges recursively; a scalar or sequence replaces the corresponding
base value; nested `null` deletes a mapping key.  A mapping for a new object
must be a complete v0.5 object.  `relations.remove` names existing relation
ids and `relations.add` contains complete relation values.  Relation ids remain
unique after resolution.  The final derived value is validated as a Project
v0.5 before scheduling.

Only objects and relations are mutable scenario scope.  A scenario MUST NOT
change `project`, `calendars`, `entities`, `extensions`, or another scenario.
It cannot select a calendar, load an extension, rename the Project identity,
or recursively inherit another scenario.  A deleted object may not remain in a
relation, annotation, parent chain, or override target; ordinary Project
validation reports those invalid derived states.

The base Project identity and bytes remain authoritative.  The derived value
has a deterministic identity composed from the primary Project content identity
and canonical `(scenario id, resolved derived Project bytes)`.  It is not a
revision-store resource and cannot be addressed independently.

## Snapshot distinction

| Property | Snapshot | Scenario |
|---|---|---|
| Meaning | agreed historical state | hypothesis about the current plan |
| Storage | separate immutable, pinned Project reference | named mapping inside primary Project |
| Drift when primary changes | none | resolves again by design |
| Evidence | snapshot revision/content identity | primary identity + scenario id + derived identity |
| View source | `snapshot` | `scenario` |

A View chooses exactly one automatic comparison baseline: `primary`,
`snapshot`, or `scenario`.  `comparison.baseline: scenario` requires
`comparison.scenario: <id>` and no Snapshot input.  Snapshot requires its
existing input and no scenario selector.  Explicit rows may use source
`{kind: scenario, scenario: <id>, object: <id>}` in addition to current source
kinds.  This allows a deliberate multi-hypothesis hand-composed row without
making automatic rows unreadable.  A scenario source does not mean an Actual
source and retains the existing overlay ordering after snapshot and before
actual.

## Resolver and diagnostics

`resolve_scenario(project, id)` is one pure, typed function at the
closure/application boundary.  It deep-copies nothing observable, performs the
specified merge, validates the resolved Project, and returns typed scheduler
input plus `ScenarioProvenance`.  Its stable failures include unknown scenario,
illegal frame field, missing/removal target, duplicate relation id, invalid
post-merge Project, and invalid selected scenario source.  Each diagnostic has
an authored scenario path; scheduler diagnostics retain their existing Project
paths after the resolver has established a valid derived input.

The render closure records selected scenario provenance adjacent to the primary
Project identity.  `render_review` schedules it exactly as it currently
schedules a snapshot.  The read ledger records `scenario` as a derived closure
input, but no Revision Store read occurs for it.  The resolver must run before
profile validation, selection, summary normalization, measurement, and Layout.

## View-projection and evidence facts

View v0.7 adds `scenario` as a comparison baseline and explicit row source.  A
scenario item is aligned by stable object id, carries source kind `scenario`,
and may be selected/grouped/ordered as other review items.  A scenario id/title
is available through declared table column source `scenario` and summary metric
source `scenario`; it is not smuggled into a title or an annotation.

The existing snapshot visual role is deliberately reused for a scenario
comparison in this issue.  A distinct scenario visual role is a future Style /
Theme decision, not a reason to duplicate the Layout or Scene pipeline.

## Architecture consistency result

- **Project → View:** pass.  persistent hypothesis semantics remain Project
  data; selecting/displaying a hypothesis remains View intent.
- **View → Layout:** pass.  projection exposes stable ids and scheduled facts,
  not Scenario geometry.
- **Layout → Scene → renderer:** pass.  no Scenario-specific placement,
  primitive kind, or target syntax is needed.
- **Closure/revision-store:** pass.  immutable primary and Snapshot evidence
  remain intact; the derived identity makes the in-memory hypothesis explicit.
- **Scheduler:** pass.  it receives only an already-valid Project and retains
  the sole authority for schedule/critical-path analysis.
- **Compatibility:** deliberately not preserved across the successor public
  contract versions; atomic resource migration prevents mixed materializable
  contexts.

## Design acceptance scenarios

1. A one-field duration override produces the same derived Project bytes and
   schedule for identical base bytes and scenario id.
2. A Scenario may add/remove objects and relations, but cannot modify a frame
   field or leave an invalid resulting Project.
3. Snapshot and Scenario with similar task values retain distinguishable source
   kind and provenance.
4. Automatic Scenario comparison shows one derived baseline; explicit rows can
   name multiple scenarios without changing automatic-row behavior.
5. The selected id/title appears only through declared View sources and output
   evidence; Layout/Scene do not inspect raw scenario mappings.
6. Existing non-scenario inputs produce byte-identical public materializer
   output after the intentional resource-version migration.
