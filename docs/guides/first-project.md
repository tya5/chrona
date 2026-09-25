# First project

Start with an editable plan, not a copied corpus:

```bash
chrona init my-first-chrona-project
chrona render my-first-chrona-project/project.yaml \
  --actual my-first-chrona-project/actual.yaml --viewport 1600xauto \
  --output my-first-chrona-project/plan.svg
```

`project.yaml` contains two tasks and a gate.  Change their titles, dates, or
add objects and relations; `actual.yaml` holds observations for the same object
identifiers.  The command uses Chrona's packaged `chrona-default-draft`
presentation preset.  The SVG is a Draft review artifact, not immutable
materializer evidence.

To select a supplied appearance explicitly, copy one into your own source tree
and render through its ordinary local preset.  Available ids are
`mission-light`, `control-room-dark`, `print-mono`, `executive-light`, and
`elevated-light`.

```bash
chrona preset copy control-room-dark --output my-first-chrona-project/looks/control-room-dark
chrona render my-first-chrona-project/project.yaml \
  --actual my-first-chrona-project/actual.yaml \
  --preset my-first-chrona-project/looks/control-room-dark/preset.yaml \
  --output my-first-chrona-project/plan.svg
```

The copied `preset.yaml`, `view.yaml`, `theme.yaml`, `scheme.yaml`, and
`layout.yaml` are ordinary editable files.  `elevated-light` uses the explicit
`chrona-output/visual/v0.7-svg` profile because that appearance requests a
v0.7 treatment; the other supplied looks use the default SVG profile.

For a complete materialized regression corpus instead, request it explicitly:

```bash
chrona init my-halcyon-corpus --example halcyon-1
```

That example's immutable closure lives in `.chrona/store`; it is runtime state,
not source to edit.  See the [root README](../../README.md) for its public
materializer command.
