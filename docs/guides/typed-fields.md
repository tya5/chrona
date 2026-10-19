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

The same declared profile works directly in a terse plan. Its package path is relative to the plan; `profile` follows
the kind, and scalar assignments come last. The checked example below compiles, then renders both ways with this guide's
View, demonstrating the same typed Project input without a separate YAML-edit step.

<!-- chrona:doc-check file: typed-plan.chrona -->
```text
terse 0.1
project typed-demo "Typed fields demo" calendar office extension team-delivery "typed-team.yaml" git:0123456789abcdef0123456789abcdef01234567
calendar office mon-fri
design "Design" task profile work 5wd from 2026-11-02 risk=low team=platform
build "Build" task profile work 10wd after design risk=high team=platform
test "Test" task profile work 5wd after build risk=medium team=product
```

```sh
chrona compile typed-plan.chrona --output typed-plan-compiled.yaml
chrona render typed-plan.chrona --preset wallboard-dark --view typed-risk-view.yaml --output typed-terse.svg
chrona render typed-plan-compiled.yaml --preset wallboard-dark --view typed-risk-view.yaml --output typed-terse-compiled.svg
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
  heading: {title: '{project}: delivery risk', subtitle: 'Bars coloured by risk'}
  surface: table-timeline
  selection:
    include: {types: [span, point]}
  colorEncoding:
    scale: series
    target: planned
    source: {field: risk}
    domain: [low, medium, high]
  grouping: {by: field, field: team, missing: Unset}
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

## 3a. Colour by field on a preset with no `series` scale

`executive-light`, `target-b` and `marquee` declare no Theme colour scale called `series`, so the
View above fails on them with `E_PRESENTATION_SCALE_MAPPING ... slots=None`. The bundled presets are
not edited; you declare the scale in your own files and pass them over the preset. Two steps:

1. **Scheme categories.** A Scheme names colours; add one category per domain value (`risk-low`,
   `risk-medium`, `risk-high`) to a copy of the preset's Color Scheme. Choose colours that keep a
   3:1 contrast against the page, or the render warns `W_SCENE_ENCODING_CONTRAST`.
2. **A derived Theme.** `chrona/theme/v0.16` names its base Theme (`extends`: the base's `id` and a `path`
   below the Theme file, with no `..`; no hash is needed) and declares only what it adds. `colorScales.series.slots` maps each domain value to a Scheme category.
   `chrona preset copy` writes the base files first.

The `executive-light` pair, with the Scheme file shown whole:

<!-- chrona:doc-check file: typed-executive-scheme.yaml -->
```yaml
version: chrona/color-scheme/v0.2
kind: color-scheme
id: executive-risk
body:
  colors:
    surface: "#FFFFFF"
    surfaceRaised: "#EAF0F8"
    text: "#172033"
    textMuted: "#4B5563"
    accent: "#3986E6"
    positive: "#269D79"
    negative: "#B91C1C"
    warning: "#8D530F"
    neutral: "#C9CED8"
    insideLabelPlanned: "#000000"
    insideLabelActual: "#000000"
    insideLabelSnapshot: "#000000"
    insideLabelScenario: "#000000"
  suitability:
    background: light
    colorVision:
    - none-claimed
    print: not-claimed
  provenance:
    kind: chrona-authored
    source: Chrona executive-light example
    license: project-pending
  categories:
    default: "#EEF3F8"
    capabilities-band: "#D8DDE6"
    risk-low: "#2E7D5B"
    risk-medium: "#B7791F"
    risk-high: "#B91C1C"
```

<!-- chrona:doc-check file: typed-executive-theme.yaml -->
```yaml
version: chrona/theme/v0.16
kind: theme
id: executive-risk
body:
  extends:
    id: chrona-builtin-executive-light
    path: looks/executive-light/theme.yaml
  roles:
    subtitle:
      fontFamily: editorial
      fontWeight: text-weight
      fontSize: text-size
      lineHeight: text-line-height
      letterSpacing: letter-spacing
      textTransform: text-transform
      numericSpacing: numeric-spacing
      iconScale: icon-scale
      iconGap: icon-gap
  colorBindings:
    subtitle.fill: textMuted
  colorScales:
    series:
      slots: {low: risk-low, medium: risk-medium, high: risk-high}
```

The same extension on `target-b` (its Scheme already has `series-1` to `series-6` for the owner
scale; the three `risk-*` categories are added after them):

<!-- chrona:doc-check file: typed-target-b-scheme.yaml -->
```yaml
version: chrona/color-scheme/v0.2
kind: color-scheme
id: target-b-risk
body:
  colors:
    surface: "#FFFFFF"
    surfaceRaised: "#EEF2F7"
    text: "#101828"
    textMuted: "#5B6B7F"
    accent: "#1D5FD1"
    positive: "#0E8A6C"
    negative: "#C0392B"
    warning: "#C77A12"
    neutral: "#C6CFDA"
    rule: "#D5DCE6"
    insideLabelPlanned: "#101828"
    insideLabelActual: "#FFFFFF"
    insideLabelSnapshot: "#000000"
    insideLabelScenario: "#000000"
  suitability:
    background: light
    colorVision:
    - none-claimed
    print: print-friendly
  provenance:
    kind: chrona-authored
    source: Chrona HALCYON-1 example, mission-light
    license: MIT
  categories:
    default: "#E8EFFA"
    period: "#1D5FD1"
    exception: "#F8E4C9"
    bar: "#C7D6F3"
    barEdge: "#3F6FD0"
    actualInk: "#101828"
    asofChip: "#B8761F"
    asofInk: "#FFFFFF"
    relationInk: "#7C8999"
    closed: "#F4F6F9"
    series-1: "#E8EFFA"
    series-2: "#E4F4EE"
    series-3: "#FBF0E1"
    series-4: "#F1E9F8"
    series-5: "#FDEBEA"
    series-6: "#D2E9F2"
    risk-low: "#2E7D5B"
    risk-medium: "#B7791F"
    risk-high: "#B91C1C"
```

<!-- chrona:doc-check file: typed-target-b-theme.yaml -->
```yaml
version: chrona/theme/v0.16
kind: theme
id: target-b-risk
body:
  extends:
    id: target-b
    path: looks/target-b/theme.yaml
  colorScales:
    series:
      slots: {low: risk-low, medium: risk-medium, high: risk-high}
```

```sh
chrona preset copy executive-light --output looks/executive-light
chrona preset copy target-b --output looks/target-b
chrona render typed-plan.yaml --preset executive-light --view typed-risk-view.yaml --theme typed-executive-theme.yaml --scheme typed-executive-scheme.yaml --output typed-risk-executive.svg
chrona render typed-plan.yaml --preset target-b --view typed-risk-view.yaml --theme typed-target-b-theme.yaml --scheme typed-target-b-scheme.yaml --output typed-risk-target-b.svg
```

Both pictures colour the bars green, amber and red and name `low`, `medium` and `high` in the legend.
`marquee` follows the same two steps with its own Scheme copy (not shown). The View
groups by `team` because `target-b`'s Layout tints its group bands and refuses `grouping: none`;
`executive-light` ignores the grouping.

### Title and subtitle

The View's `heading` sets the slide title and an optional subtitle (Spec 06): `title` and `subtitle`
are literal text with the placeholders `{project}`, `{asOf}` and `{calendar}`. The View above
declares `heading: {title: '{project}: delivery risk', subtitle: 'Bars coloured by risk'}`, and the
renders show both lines. The title works on every preset. The subtitle needs a Theme `subtitle`
typography role: `wallboard-dark` and `target-b` declare it, `executive-light` does not and fails
with `E_THEME_ROLE_REQUIRED` (`role='subtitle'`). The derived Theme above adds the role to
`executive-light` (`roles.subtitle`, built from tokens the base already defines, and the
`subtitle.fill` colour binding), so the same View renders there too. Drop `subtitle` from the View to
keep a bundled preset's Theme untouched.

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
  Section 3a shows how, with `--theme` and `--scheme`; those flags work with `--style` too.

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
