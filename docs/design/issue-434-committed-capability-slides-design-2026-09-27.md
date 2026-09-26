# Design — Committed Slides for Unexercised Capabilities (#434)

**Plan:** [design plan](../planning/active/issue-434-committed-capability-slides-design-plan-2026-09-27.md). No code semantics change; this is corpus and reporting work.

## Reporting

- **Non-default integers.** `tools/presentation_coverage.py` walks every live-schema node of `type: integer` with a declared `minimum`. It lists each value above the minimum that a committed slide declares, with the slides, in a "Non-default integer vocabulary" table. `view body.axis.tiers[].every = 2 → orion-asic/gates` appears, which meets criterion 3 by derivation rather than assertion.
- **Unreferenced files.** `tools/corpus_coverage.py` reports every `views/`, `themes/`, `layouts/`, `schemes/` and `profiles/` YAML under `examples/` that no context and no packaged preset references. Each must appear in a declared reason list inside the tool, with a one-line reason; `--check` fails on an unreferenced file without a reason. Today's two files get reasons: a derived-Theme example used by the Theme guide and tests, and a summary profile used by the CLI tests.

## Slides

- **Item 6 (leader).** Controller Z `executive-light` gives `annotation-callout-leader` its own `textMuted` stroke and a `dash.leader` token. Only `controller-z/annotations` draws leaders, so it is the only slide whose geometry-free paint changes. The other Controller Z slides change provenance only.
- **Items 1–4 and 7 (new slide `controller-z/capabilities`).** Its own copies, so no existing slide changes:
  - **View** (from `executive.yaml`): `backgroundDecoration.rows: alternate`, `grouping.presentation: band`, and a `Finish` date column after a title column declared `{fr: 1}`, so the date's inline position is fixed by the allocation and not by the title's length.
  - **Layout** (from `executive-review.yaml`): `rowDistribution: fill` and `backgroundExtents.rowBand: both`.
  - **Theme** (from `executive-light.yaml`): the table header role with `letterSpacing` and `textTransform: uppercase`, and the numeric (Δ) role set in Noto Sans Mono through the packaged mono metrics.
- **Tests:**
  - one test per capability, read from the committed Scene (stripe spans table plus timeline; rows fill the timeline; group bands with no header rows; date column position invariant under a longer title in a render with a changed title; header text transformed with letter spacing; the mono face identity used by a Δ cell);
  - a leader stroke that differs from its box's stroke.
