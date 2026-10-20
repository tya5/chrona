# Point a field at another thing: `objectReference`

A field can hold the id of another declared thing instead of a string: the deliverable a task builds,
the people who review it. That is an `objectReference` (Spec 05 §11, Spec 17). The Project keeps the
id, validation checks it, and the View shows the target's **title**. This guide declares one reference
field of each cardinality, uses them in a Project, and shows them in a table column. Every file is
written by the documented-command check and every command runs.

## 1. Declare the field

An `objectReference` field is declared in a profile package like any typed field
([Typed fields](typed-fields.md)). `targetProfiles` lists the profiles a target must have, and
`cardinality: many` takes a list. The targets are *entities*: a profile that `extends: entity` declares
a kind of thing that is not scheduled.

<!-- chrona:doc-check file: ref-profile.yaml -->
```yaml
version: chrona/profile/v0.3
packageId: atlas-delivery
contentIdentity: sha256:0000000000000000000000000000000000000000000000000000000000000000
requires:
  projectFormat: timeline/v0.7
profiles:
  atlas.work:
    extends: task
    fields:
      deliverable:
        type: objectReference
        targetProfiles: [atlas.deliverable]
      reviewers:
        type: objectReference
        cardinality: many
        targetProfiles: [atlas.person]
  atlas.deliverable:
    extends: entity
  atlas.person:
    extends: entity
```

- Without `targetProfiles` the field accepts any entity or object in the Project; give it to catch a
  reviewer id placed in `deliverable`.
- The default cardinality is `one`; a `many` field keeps the order you write.
- `required: true`, `null` and an absent field follow the same rules as every typed field.

## 2. Declare the targets, then reference them

The Project lists its targets under `entities` (or uses other `objects`), and an object puts the
**id** in `fields`. Write the id (`del-api`), never the title (`Public API v2`): titles are for
display, ids are what the Project stores.

<!-- chrona:doc-check file: ref-plan.yaml -->
```yaml
version: timeline/v0.7
project:
  id: ref-demo
  title: Reference demo
  calendar: office
extensions:
- packageId: atlas-delivery
  path: ref-profile.yaml
  revision: git:0123456789abcdef0123456789abcdef01234567
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
entities:
  del-api:
    type: atlas.deliverable
    title: Public API v2
  del-portal:
    type: atlas.deliverable
    title: Partner portal
  aiko:
    type: atlas.person
    title: Aiko
  ben:
    type: atlas.person
    title: Ben
objects:
  api:
    type: atlas.work
    title: Build the API
    fields: {deliverable: del-api, reviewers: [aiko, ben]}
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-13}
  portal:
    type: atlas.work
    title: Build the portal
    fields: {deliverable: del-portal, reviewers: [ben]}
    schedule: {mode: scheduled, amount: 10wd}
relations:
- {id: api-to-portal, type: dependency, from: {object: api, endpoint: end}, to: {object: portal, endpoint: start}, lag: 0d}
```

```sh
chrona validate ref-plan.yaml
chrona schedule ref-plan.yaml
```

A reference to an id that is not declared, or declared with a profile outside `targetProfiles`, is a
pointed `E_PROFILE_FIELD_TYPE` error at the field (for example `/objects/api/fields/deliverable`); the
`reviewers` list reports the failing element (`/objects/api/fields/reviewers/1`).

## 3. Show the titles in a table column

A table column reads the field with `source: {field: deliverable}`. The cell shows the target's title
(its id when the target has none); a `many` field shows the titles in the written order, joined by
`, `. The stored ids are unchanged, and no renderer looks anything up: the View Projection resolves them
first (Spec 06). The same field can colour bars with `colorEncoding` (`source: {field: deliverable}`,
the ids as the `domain`).

<!-- chrona:doc-check file: ref-view.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: ref-view
body:
  heading: {title: '{project}: who builds what'}
  surface: table-timeline
  rows: {mode: automatic}
  selection:
    include: {types: [span, point]}
  grouping: {by: none}
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  tableColumns:
  - {id: Task, header: {wording: column.task}, source: title, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  - {id: Deliverable, header: Deliverable, source: {field: deliverable}, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  - {id: Reviewers, header: Reviewers, source: {field: reviewers}, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  window: {mode: selected-planned, marginDays: 7}
  comparison: {baseline: primary, actual: optional, observationSelection: latest, deltaUnit: working-days, facets: [planned]}
  visibility:
    labels: {placement: table, content: [title], side: end, overflow: suppress}
    relations: {mode: semantic, overflow: suppress}
    annotations: none
  axis:
    tiers:
    - {unit: month, every: 1, role: labels, label: {form: short-month-year, align: center, overflow: thin-with-record, orientation: horizontal}}
    - {unit: week, every: 1, role: grid-minor}
```

```sh
chrona render ref-plan.yaml --preset mission-light --view ref-view.yaml --output ref.svg
```

The picture's table reads `Public API v2` and `Aiko, Ben` for the first task, and `Partner portal` and
`Ben` for the second.
