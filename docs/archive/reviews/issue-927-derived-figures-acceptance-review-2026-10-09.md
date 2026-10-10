<!-- chrona:literal-acceptance/v1 -->

# Issue #927 — derived figures acceptance

Status: selected optional scope met; issue closed after the review-containing exact-main release.

Merged source: `d4eef57f5422b31ca568ec9f174af24a704deb16` from
[PR 1259](https://github.com/tya5/chrona/pull/1259), with design and selected
scope in [issue Status](https://github.com/tya5/chrona/issues/927#issuecomment-6071114520).
The review was published in `d4c93f64ae888d335c0aa4b412e05686894bf76b`.
The exact-main release on that commit passed [run 37987979274](https://github.com/tya5/chrona/actions/runs/37987979274),
including Ubuntu, macOS and Windows pytest/conformance/wheel-smoke, MCP floor
and newest-Python public-materializer reproduction.

## Literal issue acceptance

### Issue #927

- Source: [Issue #927](https://github.com/tya5/chrona/issues/927)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for whichever is taken: synthetic tests per kind and edge date, a diagnostic for a missing fact, default output unchanged, S0 gate in the PR. | met | [Date/last-day](../../../tests/unit/chrona/core/test_figures.py), [closed counts](../../../tests/unit/chrona/core/test_figure_counts.py), [scoped facts](../../../tests/unit/chrona/usecases/test_group_figures.py) and [rendered labels](../../../tests/integration/test_figure_label_surfaces.py) cover selected kinds, edge dates and missing facts. Exact-head [PR CI 37976072590](https://github.com/tya5/chrona/actions/runs/37976072590) passed; [artifact proof 11638443781](https://github.com/tya5/chrona/pull/1259#issuecomment-6087406566) confirms 149 paths and all 140 public SVG/Scene bytes unchanged. | — |

## Programme-level criteria (optional)

- Selected scope: nine closed projected count sources, group-relative countdowns/counts, period
  `last`, literal-safe period `label.template`, and annotation-kind title/heading figures.
- Counts retain the existing behind/ahead meaning. A scalar critical-path finish
  delta or forecast is unselected under the issue's optional “whichever is taken”
  acceptance; it is neither implemented, deferred nor claimed.
- Focused figure/label suite: 232 passed (38.25s); combined annotation-figure/
  axis-scale SVG suite: 21 passed (51.18s). The three kinds share one local ID
  definition; global/group facts remain separate.
- Latest-main integration: 98 passed (10.73s), including #918 diagnostic
  provenance. The one additive AnnotationIntent merge conflict retains both
  completed figure strings and keyword-only, equality-neutral anchor provenance.
- PR S0: 451 mapped documents / 739 probes; four existing invalid documents
  unchanged; acceptance validator passed. Exact-head [CI 37976072590](https://github.com/tya5/chrona/actions/runs/37976072590)
  passed all required checks. [Artifact 11638443781](https://github.com/tya5/chrona/pull/1259#issuecomment-6087406566),
  digest `sha256:56c833decdd59c3601122505650ddd74915b190a955838375f2d0e86fa433c23`,
  has 149 before/after paths, no additions/retirements, and all 140 SVG/Scene
  files unchanged. No authored corpus/preset/flow-engine edits.

## Architecture conclusion

View projection owns selection, states and count aggregation. Core consumes immutable
neutral count/date facts without importing projection types. Presentation completes
group, period and annotation strings before measurement; Layout owns geometry, Scene
and adapters carry completed content. Group and global identities are separate;
missing facts never become zero. Existing literal captions and omitted declarations
retain their contracts. The selected implementation scope is met; scalar
critical-path forecast/day delta remains unselected and unclaimed. The exact-main
release succeeded and issue 927 is closed.
