# My first Chrona plan

`project.yaml` is your plan. `actual.yaml` is the optional observed progress
for the same objects. Both are ordinary editable source files.

Render a Draft SVG with Chrona's packaged default presentation preset:

```bash
chrona render project.yaml --actual actual.yaml --viewport 1600xauto --output plan.svg
```

`plan.svg` is a Draft for review, not immutable materializer evidence. To use
another appearance, pass an explicit preset with `--preset PATH`, or override
one of its View, Theme, Color Scheme, or Layout members; see `chrona render
--help`.
