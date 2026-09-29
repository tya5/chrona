# Attached milestones

`project.yaml` keeps a long campaign task and two independent, intermediate gates. `attachesTo` controls their presentation row, not their dates, WBS parent, or dependencies. `actual.yaml` records an eight-day slip for the first gate.

From this directory, copy the packaged `mission-light` preset and render:

```sh
chrona preset copy editorial --output preset
chrona render project.yaml --actual actual.yaml --preset preset/preset.yaml --output attached.svg --emit-scene attached.scene.json
```

The copied lane View places both gates in the campaign lane and shows their names and planned dates; the readiness label also shows `+8d`. An automatic-row View can use `rows.points: own-row` to put each gate on its own row.
