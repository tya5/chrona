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

To select an appearance explicitly, use a presentation preset:

<!-- chrona:doc-check skip: requires an author-supplied preset file -->
```bash
chrona render my-first-chrona-project/project.yaml \
  --actual my-first-chrona-project/actual.yaml --preset my-preset.yaml \
  --output my-first-chrona-project/plan.svg
```

For a complete materialized regression corpus instead, request it explicitly:

```bash
chrona init my-halcyon-corpus --example halcyon-1
```

That example's immutable closure lives in `.chrona/store`; it is runtime state,
not source to edit.  See the [root README](../../README.md) for its public
materializer command.
