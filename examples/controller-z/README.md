# Controller Z example

The **small and complete** register of the corpus: every core feature once, in eight
objects, so the board stays legible as the appearance and treatment substrate.

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
- `actual.yaml` records finished spans, a point observation for the EVB gate, an
  in-flight observation with partial progress (drawn as a progress fill), and one
  unmatched supplier record. `project.yaml` carries a `deadline` on the release gate and
  a fast-tracked negative lag between DVT and PVT.
- `contexts/elevated.yaml` binds the same evidence to the v0.6 portable visual
  profile through `themes/elevated-light.yaml`; its gradient and shadow remain
  decorative and do not replace labels or source metadata.

The corpus contains only manifest-declared materializer evidence; historic
undeclared variants were removed because they were not reproducible. Materialize
the Executive slide through `tools/materialize_example.py`.
