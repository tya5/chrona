# My first Chrona plan

`project.yaml` is your plan. `actual.yaml` is the optional observed progress
for the same objects. Both are ordinary editable source files.

Render a Draft SVG with Chrona's packaged default presentation preset:

```bash
chrona render project.yaml --actual actual.yaml --viewport 1600xauto --output plan.svg
```

To update the plan after a week of work (actuals, `asOf`, re-plan, compare with the saved plan),
see docs/guides/update-a-plan.md in the chrona repository, or the same loop in `chrona skill copy`.

`plan.svg` is a Draft for review, not immutable materializer evidence. To use
another appearance, pass an explicit preset with `--preset PATH`, or override
one of its View, Theme, Color Scheme, or Layout members; see `chrona render
--help`.
