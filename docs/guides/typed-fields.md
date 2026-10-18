# Typed fields: a profile package, a Project that uses it, a colour by one field

Some plans need fields of their own: a `risk` that is `low`, `medium` or `high`, an owner, an
`external` flag. This guide declares them once in a **profile package**, uses them from a Project, and
colours the bars by one of them. Every file below is written by the documented-command check and
every command runs, so the page cannot drift from the tool. The rules are in Spec 05 §11 (profiles
and extensions) and Spec 06 (the View's `colorEncoding`).

## 1. Write the profile package

A package names itself (`packageId`), says which Project format it targets, and declares
**profiles**. A profile `extends` a built-in object type such as `task` or `milestone` and adds typed
`fields`. Common field types are `string`, `boolean` and `enum` (with `enumValues`); `required: true`
makes a field mandatory.

<!-- chrona:doc-check file: typed-team.yaml -->
```yaml
version: chrona/profile/v0.3
packageId: team-delivery
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

## 2. Reference the package from a Project

The Project lists the package under `extensions`: its `packageId`, a `path` relative to the Project
file, and a pinned `revision: git:<40 hex>` (a moving branch name or an unpinned "latest" is invalid).
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

```sh
chrona validate typed-plan.yaml
chrona schedule typed-plan.yaml
```

## 3. Colour by the declared field

Colour is the View's job, not the plan's. `colorEncoding` names a Theme colour `scale`, the `source`
field (`{field: risk}`) and the `domain`, the values in the order they take the scale's colours.
The View below is a complete one, so it is passed with `--view` on top of a preset that has the
`series` scale (`mission-light` does; `chrona preset list` names the presets).

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
```

```sh
chrona render typed-plan.yaml --preset mission-light --view typed-risk-view.yaml --output typed-risk.svg
```

Each bar now carries the colour of its `risk` value and the legend names the values. To change a
colour, edit `fields` in the plan; never edit the picture. The same files ship with the agent skill
as `skills/chrona/examples/typed-fields/`, with a short reference page for agents.
