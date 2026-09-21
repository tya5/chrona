# ASTER Enterprise SSD sample

This fictional program demonstrates one plan with five reusable views. Dates and
observations are demonstration data.

- `project.yaml` and `actual.yaml` keep plan and observations independent.
- `views/` contains the five selections/windows.
- `themes/executive-light.yaml` supplies paint, typography and metric tokens.
- `layouts/executive-review.yaml` supplies intent-oriented composition.
- `styles/plan-actual.yaml` supplies semantic role selection.
- `contexts/01-overview.yaml` shows the generated immutable binding for one view.
- `slides/<name>/` contains only derived SVG/PNG review artifacts.

`manifest.yaml` lists these authoring resources and derived outputs. A materializer binds
one view at a time into a generated v0.4 Render Context. No slide contains Presentation
Settings, a Preset, raw coordinates, or a renderer-specific profile.

The plan exercises fixed and scheduled spans, gates, multiple calendars, exceptions,
parallel work, lag, observations and dependencies. The five views reuse the same Theme
and Layout without copying their trees or concrete token values.
