# Design — Corpus Used as Authority for the Core (#575)

**Plan:** [implementation plan](../archive/planning/issue-575-corpus-authority-implementation-plan-2026-09-30.md) (carries the baseline). **Review:** [architecture review](../archive/reviews/issue-575-corpus-authority-architecture-review-2026-09-30.md).

## Decisions

1. **Restore `avionics-bustest` to `2wd`.** Its stated purpose is gone, and the README never claims the data was wrong. The sixteen HALCYON Contexts re-pin the Project, and the corpus evidence is regenerated and reviewed against the general rule and the approved design targets, not against yesterday's bytes. HALCYON tests that assert a position or count are re-derived from the rule they stand for; if a rule has no synthetic test yet, the synthetic test lands first.
2. **Restore the `attached-milestones` data after #573.** The knob decided there (the end-gap bound, possibly measured from the item's last own mark) is what lets the original data read correctly. If it does not, the README records why the example needs a declared value, and that value is set in YAML, never in data.
3. **Synthetic fixtures for each core rule, with no `examples/` project.** A test support module builds a small project (tasks, milestones, dependencies, groups, an as-of date, actuals) as plain dictionaries in `tmp_path`, and renders it through a packaged preset copied by `chrona preset copy`. The mapping:

| Core rule | Today's test | Synthetic test |
| --- | --- | --- |
| A fixed review host reports a typed shortage and completes visibly | `11-overlay-briefing` branch of `test_public_lane_layout_projects_fixed_membership` | a packaged Layout with a fixed timeline host and more lane rows than fit: `W_LAYOUT_ROW_DENSITY`, required greater than available, rows inside the canvas |
| Fill lanes count every packed name as shown or suppressed | `test_wallboard_fill_counts_names_that_cannot_stay_near_their_marks` | `packed == shown + suppressed`, no leader primitive, no name under an annotation box |
| A member label never leaves its row band (#488) | `test_default_draft_guides_every_bar…` | every visible label inside its row band, at the bar's end or start, or counted as suppressed |
| A crowded plot selects a declared rail with a named diagnostic | `test_crowded_halcyon_plot_selects_declared_rail…` | a synthetic board with three notes and a declared rail candidate |
| Layout engine sizing, overlay and grid rules | `test_intent_engine.py` reading example Layout Profiles | frozen copies of the three profiles under `tests/fixtures/layout-profiles/`, validated by a guard test, so an edit to an example cannot change an engine test |

   The HALCYON tests stay as evidence and may fail on legitimate output changes; the synthetic ones are the gate.
4. **The written principle stays as published.** AGENTS.md and Spec 50 already say it; this issue adds tests, not text, for rows 3 to 5, and records in the acceptance review where each is satisfied.

## Boundaries

Tests, one data restoration, and (after #573) one example. No product behaviour changes in this issue. Whatever the restored data reveals in the core is fixed under a named issue, as #573 is for the label gap.
