# Controller Z example

`project.yaml` owns the plan and `actual.yaml` owns observations. Reusable presentation
inputs are organized by authority:

- `views/executive.yaml`
- `themes/executive-light.yaml` binds non-color Theme roles; `schemes/executive-light.yaml` supplies the concrete colors.
- `layouts/executive-review.yaml`
- `styles/plan-actual.yaml`
- `profiles/summary.yaml` and `profiles/review-detail.yaml`
- `contexts/executive.yaml` is the generated immutable binding example

`variants/` contains derived review artifacts and visual alternatives, never a second
layout/settings authority. Materialize the resources into one immutable snapshot, generate
a v0.4 Context/reference, and invoke `chrona render-review` as described in the
[YAML organization guide](../../docs/guides/render-review-yaml-layout.md).
