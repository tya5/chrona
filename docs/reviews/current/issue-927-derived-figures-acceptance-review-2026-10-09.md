<!-- chrona:literal-acceptance/v1 -->

# Issue #927 — derived figures acceptance

Public ready base: `7503e53076e4e0b924051b89759a9ece6ca9d038`. Design, architecture review and
implementation plan: [issue Status](https://github.com/tya5/chrona/issues/927#issuecomment-6071114520).
Implementation is on `dev-a/927-derived-figures-20261009`, not yet released.

## Literal issue acceptance

### Issue #927

- Source: [Issue #927](https://github.com/tya5/chrona/issues/927)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for whichever is taken: synthetic tests per kind and edge date, a diagnostic for a missing fact, default output unchanged, S0 gate in the PR. | not met | [Date/last-day](../../../tests/unit/chrona/core/test_figures.py), [closed counts](../../../tests/unit/chrona/core/test_figure_counts.py), [scoped facts](../../../tests/unit/chrona/usecases/test_group_figures.py) and [rendered labels](../../../tests/integration/test_figure_label_surfaces.py) pass; latest-base S0 L1/L2/L3 passes. [149-path artifact proof](https://github.com/tya5/chrona/pull/1259#issuecomment-6086768856) preserves all 140 public SVG/Scene bytes. [Critical-path scope clarification](https://github.com/tya5/chrona/issues/927#issuecomment-6073015256), fresh-head CI and exact-main release remain pending. | — |

## Programme-level criteria (optional)

- Covered: nine closed projected count sources, group-relative countdowns/counts, period
  `last`, literal-safe period `label.template`, and annotation-kind title/heading figures.
- Counts retain the existing behind/ahead meaning. The issue's critical-path wording is
  awaiting clarification; no forecast or critical-path endpoint delta is invented.
- Focused figure/label suite: 232 passed (38.25s); combined annotation-figure/
  axis-scale SVG suite: 21 passed (51.18s). The three kinds share one local ID
  definition; global/group facts remain separate.
- Latest-main integration: 98 passed (10.73s), including #918 diagnostic
  provenance. The one additive AnnotationIntent merge conflict retains both
  completed figure strings and keyword-only, equality-neutral anchor provenance.
- Latest-ready-base S0: 451 mapped documents / 739 probes; L2+L3 43.7s. Four
  existing invalid documents remain unchanged. Eight proven-stale #849 L1 entries
  are retired; seven unmerged #927 entries remain. Acceptance validator passes.
- Exact-head `dc6a02e5` [CI](https://github.com/tya5/chrona/actions/runs/37971453231)
  passed conformance, MCP, all three pytest shards and newest-Python materializers.
  Its derived-ready check failed only because main advanced; the branch now
  ordinarily merges ready `7503e530` and requires fresh checks.
- [Artifact 11637835377](https://github.com/tya5/chrona/actions/runs/37971453231/artifacts/11637835377):
  all 149 before/after paths and safe archive members checked; all 140 SVG/Scene
  bytes unchanged, two inventory/coverage reports changed, no additions/retirements.
  Digest `sha256:f4aba1bb212eb149390ae29e0f6a58a51ace9d51565a933e9468569f67d2c933`.
  No authored corpus/preset/flow-engine edits.

## Architecture conclusion

View projection owns selection, states and count aggregation. Core consumes immutable
neutral count/date facts without importing projection types. Presentation completes
group, period and annotation strings before measurement; Layout owns geometry, Scene
and adapters carry completed content. Group and global identities are separate;
missing facts never become zero. Existing literal captions and omitted declarations
retain their contracts. Release acceptance is pending.
