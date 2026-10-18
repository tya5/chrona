# Typed fields: a profile package, a Project that uses it, a colour by one field

Use this when objects need their own declared fields (a `risk` that is `low`, `medium` or `high`)
and the picture should be coloured by one. Four small files, all shipped under
`examples/typed-fields/`: run the commands from the skill directory.

## 1. Write the profile package

A package declares **profiles**. A profile `extends` a built-in object type (`task`, `milestone`, ...)
and adds typed `fields`. Common field types are `string`, `boolean` and `enum` (with `enumValues`);
`required: true` makes the field mandatory.

```yaml examples/typed-fields/team.yaml
version: chrona/profile/v0.3
packageId: team-delivery
contentIdentity: sha256:bfa83970e98192c71baea0457a20dd3e6b9a3272a900004e4b2cf485c115e644
requires:
  projectFormat: timeline/v0.7
profiles:
  work:
    extends: task
    fields:
      team:
        type: enum
        enumValues: [platform, product]
        required: true
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
    fields: {risk: low, team: platform}
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-09}
  build:
    type: work
    title: Build
    fields: {risk: high, team: platform}
    schedule: {mode: scheduled, amount: 10wd}
  test:
    type: work
    title: Test
    fields: {risk: medium, team: product}
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
and a legend (`wallboard-dark` does; `mission-light` has the scale but no legend). A full View must also
declare its `axis`, or the time axis renders blank. `chrona preset list` names the presets.

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
  axis:
    tiers:
    - unit: auto
      every: 1
      role: labels
      label:
        forms: {month: short-month-year, quarter: year-quarter, half: half-year, year: year}
        align: center
        overflow: thin-with-record
        orientation: horizontal
    - {unit: month, every: 1, role: grid-minor}
```

```bash
chrona render examples/typed-fields/plan.yaml --preset wallboard-dark --view examples/typed-fields/risk-view.yaml --output typed-fields.svg
```

Each bar takes the colour of its `risk` value, the axis shows the months and the legend names
`low`, `medium` and `high`. Edit `fields` in the plan, not the picture, and render again.

## 4. Colour only some objects with a Style

A Style rule scopes an encoding to the objects whose field matches. Give `semantic: planned` (the bars);
without it the rule also meets the labels and fails with `E_STYLE_TARGET ... semantic='memberLabel'`.
A View `colorEncoding` on the same scale conflicts with the rule, so render it over the preset's own View (no `--view`).
The preset's Theme must declare the scale (`series`): on `target-b` it fails with
`E_PRESENTATION_SCALE_MAPPING` and names the `colorScales.series.slots` or `.palette` to declare.

```yaml examples/typed-fields/style.yaml
version: chrona/style/v0.2
kind: style
id: platform-risk
body:
  rules:
    - id: platform-risk-fill
      when: {semantic: planned, fields: [{source: {field: team}, equals: platform}]}
      then:
        encode:
          channel: fill
          source: {field: risk}
          scale: series
          domain: [low, medium, high]
          legend: {title: Platform risk, showScope: true}
```

```bash
chrona render examples/typed-fields/plan.yaml --preset wallboard-dark --style examples/typed-fields/style.yaml --output typed-style.svg
```

Only the `platform` bars take their `risk` colour; the legend entries read `Platform risk: low`.
