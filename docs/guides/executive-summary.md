# Build a one-page executive summary from CSV

This recipe imports a small schedule, then renders its hierarchy at depth 1.
The visible rows are the programme and its phase groups; descendant gates stay
on their nearest retained phase row, and each selected group contributes one
summary bar. The same View works with the bundled default, `executive-light`,
and `mission-light` presets.

<!-- chrona:doc-check file: executive-plan.csv -->
```csv
id,title,type,start,end,duration,parent
programme,Product relaunch,group,,,,
design,Design,group,,,,programme
research,Customer research,task,2027-01-11,,10wd,design
design-signoff,Design sign-off,gate,2027-01-29,,,design
delivery,Delivery,group,,,,programme
build,Build,task,2027-02-01,,15wd,delivery
launch,Public launch,gate,2027-02-26,,,delivery
```

Import the CSV, then make a View that selects spans and points and groups the
Project hierarchy. At depth 1, the two gates are deeper than the displayed
grouping cutoff, but remain visible on their retained phase rows.

<!-- chrona:doc-check file: executive-view.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: executive-summary
body:
  surface: table-timeline
  rows: {mode: automatic}
  selection:
    include:
      types: [span, point]
  grouping:
    by: hierarchy
    depth: 1
    rollup: bar
    missing: ungrouped
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  window: {mode: selected-planned, marginDays: 7}
  comparison:
    baseline: primary
    actual: optional
    observationSelection: latest
    deltaUnit: calendar-days
    facets: [planned]
  visibility:
    labels:
      placement: plot
      content: [title]
      side: auto
      overflow: suppress
    fallback:
      labels: [above, below, end, start, suppress]
    relations: {mode: none, overflow: suppress}
    annotations: none
  tableColumns:
  - id: Work item
    source: title
    missing: em-dash
    align: start
    width: {minmax: {min: content, max: {fr: 1}}}
    headerOrientation: horizontal
  hierarchyColumn: Work item
```

```sh
chrona import executive-plan.csv --output executive-project.yaml \
  --calendar "standard mon-fri" --project-id product-relaunch --title "Product relaunch"
```

The default render omits `--preset` and therefore uses `chrona-default-draft`.
Mission-light packs rows tightly by default. Copy its ordinary preset
resources, then change `reviewSurface.rowDistribution` in
`executive-layout/layout.yaml` from `pack` to `fill`. Only that Layout is used
as a project-local override; the render still selects the bundled preset.
This distributes spare
canvas height among the rows without changing the View's selected items or
summary marks.

```sh
chrona preset copy mission-light --output executive-layout
```

With that Layout adjustment, render all three appearances:

```sh
chrona render executive-project.yaml --view executive-view.yaml \
  --output executive-default.svg --emit-scene executive-default.scene.json
chrona render executive-project.yaml --view executive-view.yaml --preset executive-light \
  --output executive-light.svg --emit-scene executive-light.scene.json
chrona render executive-project.yaml --view executive-view.yaml \
  --preset mission-light --layout executive-layout/layout.yaml --viewport 1600x900 \
  --output mission-light.svg --emit-scene mission-light.scene.json
```

Only the mission-light render needs the Layout override and finite viewport;
the default uses `chrona-default-draft` and the executive-light render uses its
bundled layout.
Each SVG is a Draft review artifact. The companion Scene files make it easy to
inspect the one-summary-mark-per-group and retained-gate placements.
