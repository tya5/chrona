<!-- chrona:literal-acceptance/v1 -->

# Issue #893: a Project with no calendar shades every day as closed, acceptance review

Source: [Issue #893](https://github.com/tya5/chrona/issues/893), observed 2026-10-03 (body unchanged since filing, re-fetched before this review; the comments are the implementing session's claim with owner decisions J1 and J2 and its status block, no other contributor's). The issue has no checklist; its "Acceptance proposal" is split into the three rows below. Living record: [work record](../../planning/active/issue-893-no-calendar-closed-days-2026-10-03.md); living contract [Specification 05 section 6](../../specification/05-project-format.md) and [Specification 50 section 3.4](../../specification/50-constraint-driven-gantt-surface-quality.md).

Slices: design plan, design, architecture review and implementation plan in one record, [PR #968](https://github.com/tya5/chrona/pull/968) (`24f686f1`); S1 code, Spec and tests, [PR #971](https://github.com/tya5/chrona/pull/971) (`89baf79a`). Owner decisions [on the issue](https://github.com/tya5/chrona/issues/893#issuecomment-5956488491): J1 (no declared calendar means no closed day; options: shade nothing, shade a Monday to Friday week, keep "no working day"), J2 (the closed-day legend key is listed only when a closed day is selected).

## Literal issue acceptance

### Issue #893

- Source: [Issue #893](https://github.com/tya5/chrona/issues/893)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic Project without a calendar yields no `calendar-closed` primitive and no weekend legend key. | met | `_calendar_closures` ([`v05_content.py`](../../../src/chrona/presentation/review/v05_content.py)) returns no closed and no exception day when the Project has no resolvable default calendar; `legend_entries` lists a `calendar-closed` entry only when a closed day is selected, and both the slot measurement ([`render_review.py`](../../../src/chrona/usecases/render_review.py)) and the drawing read that one list. [`test_no_calendar_closed_days.py`](../../../tests/integration/test_no_calendar_closed_days.py) (7, synthetic, no `examples/` input): no `calendar-closed` primitive and no `legend-swatch:calendar-closed` for a Project without a calendar and for calendars declared without a default; a default naming an undeclared calendar is rejected by core before presentation; the legend slot is measured without the key; the other keys remain. [`test_v05_content.py`](../../../tests/unit/chrona/presentation/review/test_v05_content.py) covers the closure set and the list. 11 of 11 mutations killed (the two measurement-side survivors of the first pass were killed by the slot-width test). The `chrona init` starter was rendered and read before and after: before, a grey plot with 78 `calendar-closed` Rects and a `WEEKEND` key; after, no shading, no key, the bars and the as-of line readable on the ground. | none |
| 2 | A Spec statement of the rule. | met | [Specification 05 section 6](../../specification/05-project-format.md) states that a Project with no default calendar has no built-in one, that Chrona assumes no Monday-to-Friday week (working-day arithmetic is `E_CALENDAR_REQUIRED`) and that a View shades no closed day; [Specification 50 section 3.4](../../specification/50-constraint-driven-gantt-surface-quality.md) ("Closed days (#893)") states that closed days come only from the declared default calendar and that the `calendar-closed` legend entry is listed only when a closed day is selected. | none |
| 3 | A Project that declares a calendar is unchanged. | met | [`test_no_calendar_closed_days.py`](../../../tests/integration/test_no_calendar_closed_days.py) renders a declared Monday-to-Friday default calendar and reads every weekend day of the window as a closed day, no weekday, with the key listed; a declared exception day closes with no weekend rule. All 40 public slides reproduce byte-identical ([`tools/regenerate_public_examples.py`](../../../tools/regenerate_public_examples.py) `--check`: PASS, 40 slides), because every corpus Project declares a default calendar (`aster-ssd`, `attached-milestones`, `controller-z`, `controller-z-ja`, `halcyon-1`, `orion-asic`); no slide was edited and none changes, so there is no changed slide to review. The starter perceptibility gate and the readable-defaults closed-day test (now on a starter with a declared calendar) pass. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Core is unchanged: the rule is the existing "a calendar only when declared" contract (Specifications 03, 04 and 05), now honoured by the presentation derivation, so scheduling and shading read the same declared fact. Content normalization owns both the closed set and the legend list derived from it; Layout still measures and draws one list, Scene and adapters are untouched, and no schema, View, Theme or diagnostic was added.

Disclosures:

- **Fixtures that relied on the defect.** Three tests built a Project without a calendar and used the all-closed shading as their closed-day fixture (the plot-edge and plot-extent tests and the starter closed-day paint test). They now declare a calendar (`sr.with_calendar`); each still proves the same rule on a declared calendar.
- **Starter.** The starter template still declares no calendar (nothing was declared), so its plot shows no weekend shading; declaring a calendar in it is an authoring choice, not part of this fix.
- **Narrow scales.** When the day scale is narrower than the Theme's closed-day minimum, Layout draws only exception days while the key is still listed if a closed day is selected; that rule predates this issue and is unchanged.

Exact review-bearing-main three-OS CI must pass before closing #893; record that run in the issue closing comment.
