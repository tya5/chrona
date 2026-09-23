# ASTER Enterprise SSD sample

This fictional program demonstrates one plan with five reusable views. Dates and
observations are demonstration data.

- `project.yaml` and `actual.yaml` keep plan and observations independent.
- `views/` contains the five selections/windows.
- `themes/executive-light.yaml` supplies typography and metric tokens; `schemes/executive-light.yaml` supplies paint.
- `layouts/executive-review.yaml` supplies intent-oriented composition.
- `styles/plan-actual.yaml` supplies semantic role selection.
- `contexts/01-overview.yaml` shows the generated immutable binding for one view.
- `slides/<name>/` contains only derived SVG/PNG review artifacts.

`manifest.yaml` lists these authoring resources and derived outputs. A materializer binds
one view at a time into a generated v0.4 Render Context. No slide contains Presentation
Settings, a Preset, raw coordinates, or a renderer-specific profile.

The plan is the **calendars and constraints** register of the corpus. It exercises fixed
and scheduled spans, gates, a five-day engineering calendar and a seven-day factory
calendar with exceptions, scheduling constraints (`min` on the pilot start, `max` on the
yield end), a `deadline` on the production release, parallel work, lag, point and
in-flight observations and dependencies. The five views reuse the same Theme
and Layout without copying their trees or concrete token values.
