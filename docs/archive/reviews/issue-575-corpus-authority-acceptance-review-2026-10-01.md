<!-- chrona:literal-acceptance/v1 -->

# Issue #575 — corpus used as authority for the core acceptance review

Source: [Issue #575](https://github.com/tya5/chrona/issues/575), observed 2026-10-01 (body last edited 2026-09-29; one owner comment, which adds the byte-identity row). Design: [#575 design](../../design/issue-575-corpus-authority-design-2026-09-30.md); [implementation plan](../planning/issue-575-corpus-authority-implementation-plan-2026-09-30.md) and [architecture review](issue-575-corpus-authority-architecture-review-2026-09-30.md), published in [PR #660](https://github.com/tya5/chrona/pull/660), merged as [`400f323d`](https://github.com/tya5/chrona/commit/400f323d22c5a3d148f2b83df0bb8fd8128eff70) ([PR CI](https://github.com/tya5/chrona/actions/runs/36724213666)).

Product slices, each merged with its PR CI green:

| Slice | PR | Merge | PR CI |
| --- | --- | --- | --- |
| I575-1 synthetic support and frozen layout profiles | [#665](https://github.com/tya5/chrona/pull/665) | [`9470fdf5`](https://github.com/tya5/chrona/commit/9470fdf53ac9afc0a9050cd39e99965ae5a7ad9c) | [run](https://github.com/tya5/chrona/actions/runs/36729405723) |
| I575-2 four synthetic surface-rule tests | [#668](https://github.com/tya5/chrona/pull/668) | [`cef53afa`](https://github.com/tya5/chrona/commit/cef53afa9bf03df59b5d21072c1e78c15276912d) | [run](https://github.com/tya5/chrona/actions/runs/36734600147) |
| I575-3 restore `avionics-bustest` lag | [#672](https://github.com/tya5/chrona/pull/672) | [`09ea4997`](https://github.com/tya5/chrona/commit/09ea4997e8f4b19fb0b67305602436de12515821) | [run](https://github.com/tya5/chrona/actions/runs/36740093429) |
| I575-4 restore attached-milestones data | [#688](https://github.com/tya5/chrona/pull/688) | [`6880bbc3`](https://github.com/tya5/chrona/commit/6880bbc352776253da9c885195989ea3d2c75f66) | [run](https://github.com/tya5/chrona/actions/runs/36752461333) |

I575-4 needed a core fix first: [#679](https://github.com/tya5/chrona/issues/679), [PR #684](https://github.com/tya5/chrona/pull/684) merged as [`cbbb3d23`](https://github.com/tya5/chrona/commit/cbbb3d236796b7256c9d21e5bccc792e7fc840a2) ([PR CI](https://github.com/tya5/chrona/actions/runs/36749948943)).

## Literal issue acceptance

### Issue #575

- Source: [Issue #575](https://github.com/tya5/chrona/issues/575)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For each corpus data edit above, either restore the original data and reach the intended look through View, Theme or Layout YAML, adding a general knob if one is missing, or record in the example's README why the data itself was wrong. A data edit made only to satisfy a rendering criterion is reverted. | met | Both edits are reverted. `avionics-bustest` is back to `2wd` and its 16 Contexts are re-pinned ([PR #672](https://github.com/tya5/chrona/pull/672)); the derived diff was reviewed against the rule and showed no defect, so no knob was needed. `attached-milestones` is back to the one-day slip ([PR #688](https://github.com/tya5/chrona/pull/688)). The original data exposed a real core limit (the readiness label sat on its own actual mark in all seven packaged presets, and no #573 knob moved it), which was fixed as a general rule in [#679](https://github.com/tya5/chrona/issues/679), not by editing data; the [example test](../../../tests/integration/test_attached_milestones.py) now asserts the label is disjoint from its own actual mark instead of only that its text exists. | — |
| 2 | Each core rule in item 2 gains a synthetic fixture test that does not load any `examples/` project. The HALCYON tests may stay as evidence. | met | [`test_synthetic_surface_rules.py`](../../../tests/integration/test_synthetic_surface_rules.py) covers the fixed-host shortage (`W_LAYOUT_ROW_DENSITY`), fill-lane packed equals shown plus suppressed, a member name inside its row band, and a crowded plot falling back to a declared rail with a named diagnostic. It uses [`synthetic_review.py`](../../../tests/support/synthetic_review.py) and reads nothing from `examples/`. The layout-profile fixtures are frozen under [`tests/fixtures/layout-profiles/`](../../../tests/fixtures/layout-profiles/) and [`test_intent_engine.py`](../../../tests/unit/chrona/presentation/layout/test_intent_engine.py) reads only them. Each test was checked by breaking the behaviour on a worktree copy (table in the PR body of #668). | — |
| 3 | Spec 50 states its criteria in neutral terms, and HALCYON appears only as an example. | met | Already on `main` before this work: [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md) says tests cover each invariant with synthetic fixtures independent of corpus projects and that corpus output demonstrates whether declared YAML reaches approved targets. No text change was needed. | — |
| 4 | **Byte identity is a no-change proof, not a quality bar.** Use a byte-identical check on corpus or public output only for changes that intend no behaviour change: refactors, resource moves, and knobs added with today's value as default. For a behaviour change, regenerate the corpus evidence and review its diff against (a) the general rule, verified by synthetic tests, and (b) the approved design targets (PR #461, the HALCYON target mock). **Current corpus output is not an oracle.** Explaining each changed primitive is for catching unintended side effects, not for preserving today's look. `AGENTS.md` and Spec 50 say this, and existing work records stop listing "automatic/HALCYON bytes unchanged" as a gate for behaviour-changing slices. | met | The rule is stated in [AGENTS.md](../../../AGENTS.md) (corpus output is evidence against approved design targets, not an oracle; byte identity proves only that a change changed nothing) and in Spec 50, both already on `main`. It was applied twice: [PR #672](https://github.com/tya5/chrona/pull/672) regenerated the corpus evidence and reviewed the 26 changed files against the rule, and [PR #684](https://github.com/tya5/chrona/pull/684) reviewed every changed slide and rejected a first variant that dropped three dependency routes before adopting a rule that changes one public slide. | — |
| 5 | `AGENTS.md` states the principle: core changes are judged by general rules and knobs, and a corpus slide's look is fixed in its YAML, or by adding a general knob, never by special-casing core behaviour or editing corpus data. | met | [AGENTS.md](../../../AGENTS.md) states it (treat corpus output as evidence against approved design targets, never a reason to edit corpus data to pass a render criterion). No text change was needed. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The core no longer depends on the corpus for its rules: each item-2 rule has a corpus-free test, both data edits are reverted, and the one rendering defect that the data edit had hidden was fixed in the core by a general rule. Byte identity was used only as a no-change proof.

Disclosures, all recorded in the work records:

- **The design pack was not complete at first.** The design linked a design-plan file that did not exist, and the plan and review were published afterwards in PR #660 (before any code). The plan's prediction that restoring `2wd` would split the `structure`, `avionics`, `bus-test` chain was disproved by the I575-3 evidence and corrected in PR #672.
- **The restored `avionics-bustest` data moves a few marks.** Lane slides 02, 11 and 12 keep their lane membership and row geometry; only the `bus-test` bar and name move left about 13 to 16 px. Mission-brief slides shift sub-pixel and show the `bus-test` and `cdr` names, so suppressed names drop from 4 to 2. One `payload-delivery` name flips from its bar's end to its start after a 0.2 px shift; the threshold was not found and nothing was tuned.
- **One coverage gap.** Removing the `bounds` check inside `place_label.legal()` is not caught by any test, because the own-mark association bound already keeps a name in its band in every fixture that could be built.
- **Open follow-ups.** [#687](https://github.com/tya5/chrona/issues/687): lane-mode names are placed before routes, so an end-side name can block a dependency route exit. The `maxEndGapEm` name is narrower than its effect (an owner decision recorded in the #573 review).

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #575; record that run in the issue closing comment.
