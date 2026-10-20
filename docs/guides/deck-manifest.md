# A deck of slides: `contextDefaults`, per-slide overrides and a baseline

A deck is one manifest that names the shared inputs once (`contextDefaults`) and lists the slides, each
with the little it changes (`contextOverrides`). `chrona materialize` composes one Render Context per
slide, draws it, and writes the SVG the manifest declares as evidence. This guide builds a two-slide
deck: the plan as it stands, and the plan against a baseline. Every file below is written by the
documented-command check and every command runs. The rules are in Spec 40 §7 (shared deck Context
authoring) and Spec 13 (the Render Context).

## 1. The files a slide reads

A slide reads a Project, a View, a Theme, a Color Scheme and a Layout Profile. The plan and the
baseline are ordinary Project files; the baseline is the plan before the last re-plan.

<!-- chrona:doc-check file: deck-project.yaml -->
```yaml
version: timeline/v0.7
project:
  id: plan
  title: Launch plan
  calendar: office
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  design:
    type: task
    title: Design
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-13}
  build:
    type: task
    title: Build
    schedule: {mode: scheduled, amount: 15wd}
  test:
    type: task
    title: Test
    schedule: {mode: scheduled, amount: 5wd}
  launch:
    type: gate
    title: Launch
    schedule: {mode: scheduled-point}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-test, type: dependency, from: {object: build, endpoint: end}, to: {object: test, endpoint: start}, lag: 0d}
- {id: test-to-launch, type: dependency, from: {object: test, endpoint: end}, to: {object: launch, endpoint: at}, lag: 0d}
```

<!-- chrona:doc-check file: deck-baseline-project.yaml -->
```yaml
version: timeline/v0.7
project:
  id: plan
  title: Launch plan
  calendar: office
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  design:
    type: task
    title: Design
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-13}
  build:
    type: task
    title: Build
    schedule: {mode: scheduled, amount: 10wd}
  test:
    type: task
    title: Test
    schedule: {mode: scheduled, amount: 5wd}
  launch:
    type: gate
    title: Launch
    schedule: {mode: scheduled-point}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-test, type: dependency, from: {object: build, endpoint: end}, to: {object: test, endpoint: start}, lag: 0d}
- {id: test-to-launch, type: dependency, from: {object: test, endpoint: end}, to: {object: launch, endpoint: at}, lag: 0d}
```

`chrona preset copy` writes a preset's View, Theme, Scheme and Layout as plain files you may edit. The
manifest below points at the copies, so the deck is yours to change:

```sh
chrona preset copy mission-light --output deck-look
```

## 2. A baseline is a `snapshot-ref` file, not the Project

A slide that compares with a baseline names it under `inputs.snapshot`. That input is **always a
separate `snapshot-ref` file** whose `body.project` is the reference to the baseline Project. Pointing
`inputs.snapshot` at the baseline Project directly is refused (`E_MATERIALIZER_MANIFEST_SCHEMA ... expected
exactly 'snapshot-ref'`), and a `snapshot-ref` file with no `body.project` is refused with
`E_MATERIALIZER_CONTEXT`; the message names the reference id, its address and `/body/project`.

<!-- chrona:doc-check file: deck-baseline-ref.yaml -->
```yaml
version: chrona/snapshot-ref/v0.3
kind: snapshot-ref
id: plan-baseline
body:
  project:
    id: plan
    kind: project
    store: {provider: local, identity: deck-demo}
    address: deck-baseline-project.yaml
    revision: {token: baseline}
```

For a `snapshot-ref` file that lacks `body.project` (here `deck-broken-ref.yaml`), materialize prints:

```text
snapshot reference plan-baseline at deck-broken-ref.yaml has no /body/project; a snapshot-ref file must embed the baseline Project reference as /body/project (id, kind: project, store, address, revision)
```

## 3. The comparing View

The second slide uses its own View: `comparison.baseline: snapshot` takes the baseline from the Render
Context, and `baselineMarks: ghost` draws each task's baseline placement as a ghost bar. Without
`baselineMarks` a snapshot baseline draws nothing by itself.

<!-- chrona:doc-check file: deck-view-compare.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: plan-compare
body:
  heading: {title: '{project}: against the baseline'}
  surface: table-timeline
  rows: {mode: automatic}
  selection:
    include: {types: [span, point]}
  grouping: {by: {fieldRole: responsible}, missing: Unassigned, fallback: hierarchy}
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  tableColumns:
    - {id: Task, header: {wording: column.task}, source: title, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  window: {mode: selected-planned, marginDays: 7}
  comparison:
    baseline: snapshot
    baselineMarks: ghost
    actual: optional
    observationSelection: latest
    deltaUnit: working-days
    facets: [planned]
  visibility:
    labels: {placement: table, content: [title], side: end, overflow: suppress}
    relations: {mode: semantic, overflow: suppress}
    annotations: {mode: none, marker: none}
  axis:
    tiers:
    - unit: month
      every: 1
      role: labels
      label: {form: short-month-year, align: center, overflow: thin-with-record, orientation: horizontal}
    - {unit: week, every: 1, role: grid-minor}
```

## 4. The manifest

`contextDefaults` is an inline, partial Context **body**: everything the slides share. Each slide gives
`contextOverrides: {id, body}`; the `id` names the composed Context and is required, and `body` holds
only what that slide changes. Rules that the first deck build tripped on:

- **`expectedSvg` is required on every slide** (`expectedScene` is optional). It is the path
  `chrona materialize` writes with `--write` and compares with otherwise; without it the manifest is
  refused (`E_MATERIALIZER_MANIFEST_SCHEMA ... missing required property 'expectedSvg'`).
- **A reference's `id` is the referenced file's own `id`**, not a name you choose: the copied View says
  `id: chrona-preset-mission-light`, so the reference uses that id (`E_CLOSURE_ID` otherwise).
- `fontMetrics` needs `algorithm` and `missingFont` beside the packaged `fontSet`.
- Members merge by name; `inputs` and `environment` merge one level deep; a whole reference, `viewport`
  or `fontMetrics` is replaced, never merged field by field. An explicit `null` removes a member
  (`inputs: {snapshot: null}` is a slide without the baseline).
- Local files are addressed relative to the manifest and need a `store` (`provider: local`, any
  `identity`); `revision.token` is a label you choose.

<!-- chrona:doc-check file: deck-manifest.yaml -->
```yaml
version: chrona/example-materializer/v0.1
id: deck-demo
role: regression-corpus
contextDefaults:
  project:
    id: plan
    kind: project
    store: {provider: local, identity: deck-demo}
    address: deck-project.yaml
    revision: {token: current}
  view: {id: chrona-preset-mission-light, kind: view, store: {provider: local, identity: deck-demo}, address: deck-look/view.yaml, revision: {token: v1}}
  theme: {id: chrona-builtin-mission-light, kind: theme, store: {provider: local, identity: deck-demo}, address: deck-look/theme.yaml, revision: {token: v1}}
  colorScheme: {id: mission-light, kind: color-scheme, store: {provider: local, identity: deck-demo}, address: deck-look/scheme.yaml, revision: {token: v1}}
  layout: {id: chrona-builtin-mission-light, kind: layout-profile, store: {provider: local, identity: deck-demo}, address: deck-look/layout.yaml, revision: {token: v1}}
  inputs:
    snapshot:
      id: plan-baseline
      kind: snapshot-ref
      store: {provider: local, identity: deck-demo}
      address: deck-baseline-ref.yaml
      revision: {token: baseline}
  environment:
    viewport: {inlineSize: 1600, blockSize: 900}
    locale: en-US
    fontMetrics: {algorithm: declared-metrics-v3, missingFont: diagnose, fontSet: chrona.noto-sans}
    scenePrecision: 3
  target:
    kind: svg
    visualProfile: chrona-output/visual/v0.6-svg
    capabilities: [accessibleText, hierarchicalAxis, marker, semanticRoles, sourceMetadata, tableSemantics]
slides:
- id: overview
  expectedSvg: deck-generated/overview.svg
  evidence: the plan as it stands
  contextOverrides:
    id: deck-overview
- id: compare
  expectedSvg: deck-generated/compare.svg
  evidence: the plan against its baseline
  contextOverrides:
    id: deck-compare
    body:
      view: {id: plan-compare, kind: view, store: {provider: local, identity: deck-demo}, address: deck-view-compare.yaml, revision: {token: v1}}
```

## 5. Write the evidence, then check it

`--write` writes `expectedSvg`; the output directory receives the SVG and the composed `closure.yaml`. Run the command without `--write` to check
that the committed evidence still matches; a mismatch is `E_MATERIALIZER_MISMATCH`.

```sh
chrona materialize deck-manifest.yaml --slide overview --output deck-write-overview --write
chrona materialize deck-manifest.yaml --slide compare --output deck-write-compare --write
chrona materialize deck-manifest.yaml --slide overview --output deck-check-overview
chrona materialize deck-manifest.yaml --slide compare --output deck-check-compare
```

The `overview` slide inherits every default, including the baseline input, but its View does not compare
with it, so the baseline is unused there; the `compare` slide replaces only the View. To add a slide,
add an entry; to change what every slide shares, change `contextDefaults`.
