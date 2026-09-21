# Issue #38 reproducibility implementation plan

1. Repair the acceptance test's version/schema selection and add source-context coverage.
2. In the materializer, derive a copied context with SHA-256 identities for project, view, theme, color scheme, layout, inputs, nested snapshot project, and declared font assets; invoke `render-review --require-content-identity`.
3. Add per-slide manifest-context regression coverage and make the materializer integration test enumerate declared slides.
4. Publish implementation review after public materialization and delegated pytest evidence; close #38 only then.

Implementation begins after this plan and review are published.