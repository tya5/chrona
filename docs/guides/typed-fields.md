# Typed fields: a profile package, a Project that uses it, a colour by one field

Some plans need fields of their own: a `risk` that is `low`, `medium` or `high`, an owner, an
`external` flag. This guide declares them once in a **profile package**, uses them from a Project, and
colours the bars by one of them. Every file below is written by the documented-command check and
every command runs, so the page cannot drift from the tool. The rules are in Spec 05 §11 (profiles
and extensions), Spec 06 (the View's `colorEncoding`) and Spec 07 (Style rules).

## 1. Write the profile package

A package names itself (`packageId`), says which Project format it targets, and declares
**profiles**. A profile `extends` a built-in object type such as `task` or `milestone` and adds typed
`fields`. Common field types are `string`, `boolean` and `enum` (with `enumValues`); `required: true`
makes a field mandatory.

<!-- chrona:doc-check file: typed-team.yaml -->
```yaml
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

## 2. Reference the package from a Project

The Project lists the package under `extensions`: its `packageId`, a `path` relative to the Project
file, and a pinned `revision: git:<40 hex>` (a moving branch name or an unpinned "latest" is invalid).
The `path` must stay inside the Project's directory: a parent directory (`../`), an absolute path or a
`.` segment is not permitted, so write `extensions/typed-team.yaml`, not `../../profile.yaml`.
An object then uses the profile as its `type` and gives each field a value under `fields`. Dates
still come from `schedule`; a field never moves a bar.

<!-- chrona:doc-check file: typed-plan.yaml -->
```yaml
version: timeline/v0.7
project:
  id: typed-demo
  title: Typed fields demo
  calendar: office
extensions:
- packageId: team-delivery
  path: typed-team.yaml
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

```sh
chrona validate typed-plan.yaml
chrona schedule typed-plan.yaml
```

## 3. Colour by the declared field

Colour is the View's job, not the plan's. `colorEncoding` names a Theme colour `scale`, the `source`
field (`{field: risk}`) and the `domain`, the values in the order they take the scale's colours.
The View below is a complete one, so it is passed with `--view` on top of a preset that has the
`series` scale and a legend (`wallboard-dark` does; `mission-light` has the scale but no legend;
`chrona preset list` names the presets). A complete View also declares its `axis`: without it the time
axis renders blank, so the `axis` block below is part of the example.

<!-- chrona:doc-check file: typed-risk-view.yaml -->
```yaml
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

```sh
chrona render typed-plan.yaml --preset wallboard-dark --view typed-risk-view.yaml --output typed-risk.svg
```

Each bar now carries the colour of its `risk` value, the axis labels the months and the legend names
`low`, `medium` and `high`. To change a colour, edit `fields` in the plan; never edit the picture.

## 4. Colour only some objects with a Style

A **Style** rule scopes an encoding to the objects whose field matches (`fields` predicates need the
profile's declarations). The rule below colours only the `platform` team's bars by `risk`; the other
bars keep the preset's plain colour, and `showScope: true` makes the legend read `Platform risk: low`.
Three rules to know:

- Give `semantic: planned` (the bars). Without it the rule also meets the labels and fails with
  `E_STYLE_TARGET ... semantic='memberLabel'`.
- A View `colorEncoding` that uses the same scale with another domain conflicts with the rule, so
  render this Style over the preset's own View (no `--view`).
- The preset's Theme must declare the scale. On `target-b` the render fails with
  `E_PRESENTATION_SCALE_MAPPING ... slots=None` and the message names what to declare:
  `colorScales.series.slots` (one Scheme category per domain value) or `colorScales.series.palette`.

<!-- chrona:doc-check file: typed-style.yaml -->
```yaml
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

```sh
chrona render typed-plan.yaml --preset wallboard-dark --style typed-style.yaml --output typed-style.svg
```

The same files ship with the agent skill as `skills/chrona/examples/typed-fields/`, with a short
reference page for agents.
