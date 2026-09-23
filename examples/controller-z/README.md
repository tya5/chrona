# Controller Z example

`project.yaml` owns the plan and `actual.yaml` owns observations. Reusable presentation
inputs are organized by authority:

- `views/executive.yaml`
- `themes/executive-light.yaml` binds non-color Theme roles; `schemes/executive-light.yaml` supplies the concrete colors.
- `layouts/executive-review.yaml`
- `presets/executive-light.yaml` is a public declarative preset whose ordinary
  presentation resources are the ones pinned by the Executive Context.
- `styles/plan-actual.yaml`
- `profiles/summary.yaml` and `profiles/review-detail.yaml`
- `contexts/executive.yaml` is the generated immutable binding example

The corpus contains only manifest-declared materializer evidence; historic
undeclared variants were removed because they were not reproducible. Materialize
the Executive slide through `tools/materialize_example.py`.
