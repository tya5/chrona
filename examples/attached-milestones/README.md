# Attached milestones

`project.yaml` keeps a long campaign task and two independent, intermediate gates. `attachesTo` controls their presentation row, not their dates, WBS parent, or dependencies. `actual.yaml` records a one-day slip for the first gate.

From this directory, copy the packaged `mission-light` preset and render:

```sh
chrona preset copy mission-light --output preset
chrona render project.yaml --actual actual.yaml --preset preset/preset.yaml --output attached.svg --emit-scene attached.scene.json
```

The default lane View places both gates in the campaign lane and shows their names and planned dates; the readiness label also shows `+1d`. An automatic-row View can use `rows.points: own-row` to put each gate on its own row.

The readiness label sits after its own actual mark and never on it (Spec 50 §3.2). An attached label is drawn over its parent campaign bar, so the render reports `W_LAYOUT_LABEL_OVERFLOW` (`label-collision`) for each gate; that warning is expected for this example.
