<!-- chrona:literal-acceptance/v1 -->

# Issue #927 — derived figures acceptance

Public base: `4c7f3b616a95749678260483546dda26a975e944`. Design, architecture review and
implementation plan: [issue Status](https://github.com/tya5/chrona/issues/927#issuecomment-6071114520).
Implementation is on `dev-a/927-derived-figures-20261009`, not yet released.

## Literal issue acceptance

### Issue #927

- Source: [Issue #927](https://github.com/tya5/chrona/issues/927)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for whichever is taken: synthetic tests per kind and edge date, a diagnostic for a missing fact, default output unchanged, S0 gate in the PR. | not met | [Date and last-day tests](../../../tests/unit/chrona/core/test_figures.py), [closed count tests](../../../tests/unit/chrona/core/test_figure_counts.py), [scoped facts](../../../tests/unit/chrona/usecases/test_group_figures.py), [rendered labels](../../../tests/integration/test_figure_label_surfaces.py); local S0 L1/L2/L3 passed. PR snapshot, public byte audit and release gates pending. | — |

## Programme-level criteria (optional)

- Covered: nine closed projected count sources, group-relative countdowns/counts, period
  `last`, literal-safe period `label.template`, and annotation-kind title/heading figures.
- Counts retain the existing behind/ahead meaning. The issue's critical-path wording is
  awaiting clarification; no forecast or critical-path endpoint delta is invented.
- Focused runs: 176 group regressions, 142 annotation regressions, 76 count/label/helper
  tests, 45 final label tests and 40 contract/fact tests passed (overlapping suites).
- S0: 443 mapped documents and 739 probes, L2+L3 39.8s; annotation lint passed.
- No corpus/preset source edits. Actual public SVG/Scene byte identity and every required
  CI check remain acceptance requirements, not inferred from synthetic tests.

## Architecture conclusion

View projection owns selection, states and count aggregation. Core consumes immutable
neutral count/date facts without importing projection types. Presentation completes
group, period and annotation strings before measurement; Layout owns geometry, Scene
and adapters carry completed content. Group and global identities are separate;
missing facts never become zero. Existing literal captions and omitted declarations
retain their contracts. Release acceptance is pending.
