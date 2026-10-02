# Implementation Plan — Axis Ticks at Interval Starts (#492)

**Design:** [design](../../design/issue-492-axis-ticks-design-2026-10-02.md), [architecture review](../../reviews/current/issue-492-axis-ticks-architecture-review-2026-10-02.md). **Normative:** [Specification 39](../../specification/39-axis-and-observation-clarity.md), "Axis ticks (#492)".

One code PR (slice I492-1), then the acceptance review.

## I492-1 — `tickLength`

- **Schema:** add the optional role property `tickLength` (named token) to `schemas/theme-v0.11.schema.yaml` and `schemas/theme-v0.13.schema.yaml`, in place. Run `python -m tools.schema_equivalence --base-rev origin/main` and record the result in the PR; add an L1 delta entry only if the gate asks for one.
- **Role admission:** `presentation/scene/capabilities.py`, give `axis-major` and `axis-minor` their own contract (`_PATH_PAINT` plus `tickLength`, in `_LAYOUT_GEOMETRY`).
- **Layout:** `presentation/layout/surface_axis.py`, the `grid-*` branch: read `tickLength` once per role; with it, complete the two-point Path from the axis slot bottom up by the length; raise `E_PRESENTATION_AXIS_INVALID` for a length of zero or less and `E_PRESENTATION_AXIS_OVERFLOW` for a length above the slot block size.
- **Scene, View, adapters, registry:** unchanged.
- **Tests (synthetic, no `examples/` input):** a new unit test module next to `test_v05_builder.py`, built on its `_axis_tiers_scene` helper: ticks of the declared length standing on the slot bottom at every week start; a month tier in the same View with no property stays full height; identical points with no property (byte identity of the default); positions equal the full-height line's; both roles; non-positive and oversized lengths fail with the named codes; a theme that puts `tickLength` on another role is rejected by admission. **Mutation check:** break the length, the anchor, the guard and the admission, and confirm each test fails.
- **Committed slide:** Controller Z `axis-ticks` (view v0.28, Theme, context, manifest entry), regenerated with `tools/regenerate_public_examples.py`; the SVG is viewed and checked by eye.
- **Evidence:** `--check` of the corpus is byte-identical for every existing slide; the only new files are the slide's SVG and Scene. Conformance passes.
- **Publication boundary:** one PR, `Refs #492`; no preset, Project schema, Scene or legend file.

## Acceptance review

`docs/reviews/current/issue-492-axis-ticks-acceptance-review-<date>.md` with the `chrona:literal-acceptance/v1` marker, one row for the literal criterion, checked by `tools/check_issue_acceptance_reviews.py`; then the exact-main three-OS run on the review commit.
