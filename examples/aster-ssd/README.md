# ASTER Enterprise SSD sample

This fictional program demonstrates one plan with one reproducible overview.
Dates and observations are demonstration data.

- `project.yaml` and `actual.yaml` keep plan and observations independent.
- `views/01-overview.yaml` contains the manifest-selected presentation intent.
- `themes/executive-light.yaml` supplies typography and metric tokens; `schemes/executive-light.yaml` supplies paint.
- `layouts/executive-review.yaml` supplies intent-oriented composition.
- `contexts/01-overview.yaml` shows the generated immutable binding for one view.
- `generated/overview.svg` and `generated/overview.scene.json` are checked
  materializer evidence.

`manifest.yaml` lists these authoring resources and derived outputs. A materializer binds
one view at a time into a generated v0.4 Render Context. No slide contains Presentation
Settings, a Preset, raw coordinates, or a renderer-specific profile.

The plan is the **calendars and constraints** register of the corpus. It exercises fixed
and scheduled spans, gates, a five-day engineering calendar and a seven-day factory
calendar with exceptions, scheduling constraints (`min` on the pilot start, `max` on the
yield end), a `deadline` on the production release, parallel work, lag, point and
in-flight observations and dependencies.
