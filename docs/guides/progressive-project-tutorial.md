# Project features, one step at a time

Start with [your first project](first-project.md). Then open each small,
independent Project below. Every stage is a complete input, so you can change
it without carrying edits from an earlier stage. The first six use the
packaged default presentation; the seventh adds an Actual Set. These are
editable Draft renders, not byte-pinned published evidence.

| Stage | New concept | Source |
| --- | --- | --- |
| 1 | Two fixed-span tasks | [Project](../../examples/onboarding/01-spans/project.yaml) |
| 2 | A fixed-point decision gate | [Project](../../examples/onboarding/02-gate/project.yaml) |
| 3 | Dependency edges and a two-day lag | [Project](../../examples/onboarding/03-relations/project.yaml) |
| 4 | Working-day calendar and one exception | [Project](../../examples/onboarding/04-calendar/project.yaml) |
| 5 | Scheduled-end constraint and gate deadline | [Project](../../examples/onboarding/05-constraints/project.yaml) |
| 6 | Parent/child hierarchy and rollup schedule | [Project](../../examples/onboarding/06-rollup/project.yaml) |
| 7 | Observed dates and progress | [Project](../../examples/onboarding/07-actuals/project.yaml), [Actual Set](../../examples/onboarding/07-actuals/actual.yaml), [progress View](../../examples/onboarding/07-actuals/view.yaml) |

Run each command, compare the result with the preceding stage, and edit a
title or date in that stage's Project before rendering it again:

```bash
chrona render examples/onboarding/01-spans/project.yaml --output tutorial-01.svg
chrona render examples/onboarding/02-gate/project.yaml --output tutorial-02.svg
chrona render examples/onboarding/03-relations/project.yaml --output tutorial-03.svg
chrona render examples/onboarding/04-calendar/project.yaml --output tutorial-04.svg
chrona render examples/onboarding/05-constraints/project.yaml --output tutorial-05.svg
chrona render examples/onboarding/06-rollup/project.yaml --output tutorial-06.svg
chrona render examples/onboarding/07-actuals/project.yaml \
  --actual examples/onboarding/07-actuals/actual.yaml \
  --view examples/onboarding/07-actuals/view.yaml --output tutorial-07.svg
```

The next three concepts cross source boundaries. A scenario is declared in
the [Project](../../examples/halcyon-1/project.yaml) but is visible only
because the [View](../../examples/halcyon-1/views/06-flight-readiness.yaml)
selects it. A prior-plan comparison uses a
[snapshot reference](../../examples/halcyon-1/snapshots/baseline-2027-06.yaml)
from [Render Context](../../examples/halcyon-1/contexts/07-replan-baseline.yaml),
not from an editable Draft Project. An extension is declared in the
[ORION Project](../../examples/orion-asic/project.yaml) and resolved from a
[pinned profile package](../../examples/orion-asic/extensions/semiconductor-development.yaml).
The public materializer follows each immutable closure and reproduces its
committed SVG/Scene bytes:

```bash
chrona materialize examples/halcyon-1/manifest.yaml --slide flight-readiness --output tutorial-scenario
chrona materialize examples/halcyon-1/manifest.yaml --slide replan-baseline --output tutorial-snapshot
chrona materialize examples/orion-asic/manifest.yaml --slide gates --output tutorial-extension
```

Look at the generated `review.svg`, `review.scene.json`, and `closure.yaml`
inside each output directory. The scenario Scene records its selected
scenario, the snapshot slide compares the captured baseline, and ORION shows
the extension-typed gates. To change those advanced inputs, author a new
Project/View/Context closure deliberately; do not edit a materialized
snapshot as if it were Draft source.
