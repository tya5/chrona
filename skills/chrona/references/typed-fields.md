# Typed fields: a profile package, a Project that uses it, a colour by one field

Use this when objects need their own declared fields (a `risk` that is `low`, `medium` or `high`)
and the picture should be coloured by one. Three small files, all shipped under
`examples/typed-fields/`: run the commands from the skill directory.

## 1. Write the profile package

A package declares **profiles**. A profile `extends` a built-in object type (`task`, `milestone`, ...)
and adds typed `fields`. Common field types are `string`, `boolean` and `enum` (with `enumValues`);
`required: true` makes the field mandatory.

```yaml examples/typed-fields/team.yaml
version: chrona/profile/v0.3
packageId: team-delivery
contentIdentity: sha256:c81ab89626b1fb23f4a7187219d4d097252c4c3c37bad28ebbe75cec0384e046
requires:
  projectFormat: timeline/v0.7
profiles:
  work:
    extends: task
    fields:
      risk:
        type: enum
        enumValues: [low, medium, high]
        required: true
```

## 2. Reference it from the Project

List the package under `extensions` (`packageId`, a `path` relative to the Project file, and a
pinned `revision: git:<40 hex>`), then give each object the profile as its `type` and a value for
each field under `fields`. The dates still come from `schedule`, never from a field.

```yaml examples/typed-fields/plan.yaml
version: timeline/v0.7
project:
  id: typed-demo
  title: Typed fields demo
  calendar: office
extensions:
- packageId: team-delivery
  path: team.yaml
  revision: git:0123456789abcdef0123456789abcdef01234567
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  design:
    type: work
    title: Design
    fields: {risk: low}
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-09}
  build:
    type: work
    title: Build
    fields: {risk: high}
    schedule: {mode: scheduled, amount: 10wd}
  test:
    type: work
    title: Test
    fields: {risk: medium}
    schedule: {mode: scheduled, amount: 5wd}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-test, type: dependency, from: {object: build, endpoint: end}, to: {object: test, endpoint: start}, lag: 0d}
```

```bash
chrona validate examples/typed-fields/plan.yaml
chrona schedule examples/typed-fields/plan.yaml
```

## 3. Colour by the declared field

Colour belongs to the View, never the plan. A View's `colorEncoding` names a Theme colour `scale`,
the `source` field (`{field: risk}`) and the `domain`, the values in the order they take the scale's
colours. This View is a full one, so pass it with `--view` over a preset that has the `series` scale
(`mission-light` does). `chrona preset list` names the presets.

```yaml examples/typed-fields/risk-view.yaml
version: chrona/view/v0.28
kind: view
id: risk-view
body:
  surface: table-timeline
  selection:
    include: {types: [span, point]}
  colorEncoding:
    scale: series
    target: planned
    source: {field: risk}
    domain: [low, medium, high]
  grouping: {by: none}
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  window: {mode: selected-planned}
  comparison: {baseline: primary, actual: optional, observationSelection: latest, deltaUnit: working-days, facets: [planned]}
  visibility:
    labels: {placement: plot, content: [title], side: end, overflow: suppress}
    relations: {mode: semantic, overflow: suppress}
    annotations: none
  rows:
    mode: lanes
    laneTable: {label: lane}
```

```bash
chrona render examples/typed-fields/plan.yaml --preset mission-light --view examples/typed-fields/risk-view.yaml --output typed-fields.svg
```

Each bar takes the colour of its `risk` value, and the legend names the values. Edit `fields`
in the plan, not the picture, and render again.
