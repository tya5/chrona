# Render a dependency network from a CSV plan

A network View selects Project objects and their dependency edges instead of
placing them on a time axis. The bundled presets provide reusable Theme and
Scheme resources, but their Layouts have timeline slots, not a `network`
slot. Select a compatible Layout explicitly with `--layout`, as below.
No repository checkout or example project is needed.

<!-- chrona:doc-check file: network-plan.csv -->
```csv
id,title,start,end,duration,predecessors
design,Design,2027-03-01,2027-03-05,,
build,Build,,,5d,design
test,Test,,,3d,build
```

<!-- chrona:doc-check file: network-view.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: csv-network
body:
  surface: dependency-network
  rows: {mode: automatic}
  selection: {include: {types: [span, point]}}
  grouping: {by: none}
  ordering: {by: plannedStart, direction: ascending, tieBreak: id}
  window: {mode: selected-planned}
  comparison: {baseline: primary, actual: forbidden, observationSelection: latest, deltaUnit: calendar-days, facets: [planned]}
  visibility: {labels: false, relations: semantic, annotations: none}
  network: {nodeLabel: {source: title}}
```

<!-- chrona:doc-check file: network-layout.yaml -->
```yaml
version: chrona/layout-profile/v0.10
id: csv-network-layout
flowDirection: horizontal
dependencyNetworkFlowDirection: horizontal
requiredThemeTokens: [spacing.l, spacing.m]
reviewSurface:
  rowDistribution: pack
  backgroundExtents: {rowBand: table, groupBand: timeline, groupHeaderBand: both, calendarClosed: timeline}
  annotationRouting: {maxBends: 4, maxDetourRatio: 2}
relationRouting: {maxBends: 4, maxDetourRatio: 2}
root:
  id: page
  kind: column
  inlineSize: fill
  blockSize: fill
  gap: {token: spacing.m}
  padding: {token: spacing.l}
  alignItems: stretch
  justifyContent: start
  children:
    - id: title
      kind: slot
      source: title
      inlineSize: content
      blockSize: content
      place: {inline: start, block: start, safety: safe}
      priority: required
      overflow: visible-overflow
    - id: network
      kind: slot
      source: network
      inlineSize: fill
      blockSize: fill
      place: {inline: stretch, block: stretch, safety: strict}
      priority: required
      overflow: visible-overflow
```

Save the three files above in the same working directory, then run:

```sh
chrona import network-plan.csv --output network-project.yaml --title "Delivery dependencies"
chrona render network-project.yaml --preset control-room-dark --view network-view.yaml --layout network-layout.yaml --viewport 1200x600 --output network.svg
chrona render network-project.yaml --preset control-room-dark --view network-view.yaml --layout network-layout.yaml --viewport 1200x600 --output network.png
```

The output contains three labelled nodes and two directed dependencies. The
Layout owns node placement and routing; changing the View does not turn a
timeline slot into a network slot. `E_PRESENTATION_PRIMITIVE_MISSING` at
`/layoutManifest/sources/network` means the selected Layout needs that slot:
use the `network-layout.yaml` above instead of the preset's timeline Layout.

`network.nodeLabel.source` may also be `id`, `{field: column-name}` or
`{fieldRole: phase}`. A missing field uses the Project title. Network Views
do not take timeline-only members such as `axis`, `tableColumns` or `shading`;
remove such authored members rather than copying a timeline View wholesale.
