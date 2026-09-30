<!-- chrona:literal-acceptance/v1 -->

# Issue #679 — member-name reach from the last own mark acceptance review

Source: [Issue #679](https://github.com/tya5/chrona/issues/679), observed 2026-10-01 (no comments; body unchanged since 2026-09-30). Found by #575 I575-4; the deferred decision 3 of the [#573 design](../../design/issue-573-label-behaviour-knobs-design-2026-09-30.md). Plan slice and review addendum: [#573 implementation plan](../../planning/active/issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md) (slice I679-1) and [#573 architecture review](issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md), published in [PR #680](https://github.com/tya5/chrona/pull/680) (merged as [`ee28ed72`](https://github.com/tya5/chrona/commit/ee28ed72b1ec218551fc78e7c2527f1c362ead9f), [PR CI](https://github.com/tya5/chrona/actions/runs/36744216681)) and narrowed in [PR #681](https://github.com/tya5/chrona/pull/681) (merged as [`9c8bab8f`](https://github.com/tya5/chrona/commit/9c8bab8fd7008053174dbe4a7e90ad4eaf82f062), [PR CI](https://github.com/tya5/chrona/actions/runs/36746703155)). Code: [PR #684](https://github.com/tya5/chrona/pull/684) merged as [`cbbb3d23`](https://github.com/tya5/chrona/commit/cbbb3d236796b7256c9d21e5bccc792e7fc840a2) ([PR CI](https://github.com/tya5/chrona/actions/runs/36749948943)). Data restore: [PR #688](https://github.com/tya5/chrona/pull/688) merged as [`6880bbc3`](https://github.com/tya5/chrona/commit/6880bbc352776253da9c885195989ea3d2c75f66) ([PR CI](https://github.com/tya5/chrona/actions/runs/36752461333)).

## Literal issue acceptance

### Issue #679

- Source: [Issue #679](https://github.com/tya5/chrona/issues/679)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The reach is measured from the item's last own drawn mark; a synthetic test (no `examples/` input) shows a member label never overlaps its own actual or baseline mark when a valid candidate exists, and that the reach still bounds detached text. | narrowed | The rule as merged is narrower than the row's first clause: the declared side ladder and every host-measured candidate stay as they were, and "end after the rightmost own mark, reach measured from its right edge" is added as a final rung, used only when no ladder candidate is legal (plus a visible-overflow fallback measured from the same edge). A first variant that applied the rule inside the ordinary ladder lost three dependency routes on public slides and was rejected ([PR #681](https://github.com/tya5/chrona/pull/681)). The [synthetic rule tests](../../../tests/integration/test_synthetic_surface_rules.py) use no `examples/` input and cover the no-overlap rule and a name with a legal ladder candidate staying unchanged; the [unit tests](../../../tests/unit/chrona/presentation/layout/test_member_name_own_marks.py) cover the final rung, that the reach still bounds detached text, and the fallback. Replacing the own-mark lookup with the host-only version makes the rule test fail (mutation check in the PR body). | [#687](https://github.com/tya5/chrona/issues/687) (lane names are placed before routes) |
| 2 | Corpus and public evidence is regenerated and the diff of each changed slide is reviewed against the general rule and the approved design targets (PR #461, the HALCYON target mock); every changed primitive is explained, none is kept only to preserve today's look. | met | The evidence was regenerated locally and every changed file reviewed before merge, and the review table is in the [PR #684 body](https://github.com/tya5/chrona/pull/684): exactly one public slide changed, `aster-ssd/overview`, where `member-label:ftl:ftl` is now emitted after its own actual bar and `W_LAYOUT_LABEL_SUPPRESSED` plus `I_LAYOUT_PLOT_LABELS_SUPPRESSED` are gone, matching the sibling rows; no route, dependency or annotation changed on any other example. The rejected first variant's five-slide change (three lost dependency routes) is recorded in the [review addendum](issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md). | — |
| 3 | `examples/attached-milestones/actual.yaml` and its README are restored to the original data (#575 I575-4), with a test that the label does not overlap its own actual mark. | met | [PR #688](https://github.com/tya5/chrona/pull/688) restores the one-day slip and the README, and the [example test](../../../tests/integration/test_attached_milestones.py) asserts the readiness label is disjoint from its own actual mark in the packaged `mission-light` preset. With the original data the label no longer sits on its actual mark in any of the seven packaged presets (measured before the restore in a temporary copy). | — |
| 4 | Spec 50 §3.2 states where the reach is measured from. | met | [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md) states that an item's own marks are its planned and actual marks (an absence indicator is not one), that the ladder is unchanged, and that the name goes after the right edge of the rightmost own mark only when no ladder candidate is legal, with the reach measured from that edge. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout-only: a final rung and a fallback measurement inside member-name placement, no schema, Scene contract or adapter change, and `maxEndGapEm` keeps its default of 2 em. Row 1 is `narrowed`, not `met`, on purpose: measuring the reach from the last mark everywhere moved legal names and cost dependency lines, so the rule applies only where today a name would be suppressed or overflow; that is the narrower behaviour the rows' intent (a label never sits on its own mark) needs, and applying the rule more widely depends on the route-exit question recorded in #687.

Disclosures:

- **Attached labels still report a collision.** With the original attached-milestones data each gate label overlaps its parent campaign bar by design, so `W_LAYOUT_LABEL_OVERFLOW` (`label-collision`) remains, as it does with the committed eight-day data the example had before.
- **`maxEndGapEm` is narrower than its effect.** It now bounds the ladder end gap, the association distance and the final-rung gap. Renaming it is a public schema change left as an owner decision.
- **An unchecked example.** With the old eight-day data the label would now run over the `range-clearance` gate; that data is no longer committed.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #679; record that run in the issue closing comment.
