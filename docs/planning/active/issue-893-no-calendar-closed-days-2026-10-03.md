# Issue #893: a Project with no calendar shades every day as closed (work record)

Living record for [#893](https://github.com/tya5/chrona/issues/893) (P1 on the read-only board #454). One small record holds the baseline, design plan, design, architecture review and implementation plan; it is published before any code.

**Public base:** `5eeb128e` on `main`. **Status:** design published here; code not started. Related: [#880](https://github.com/tya5/chrona/issues/880) (closed; found this on the `chrona init` starter and filed it).

## 1. Published baseline

Read on `5eeb128e` from code, the Specification and a rendered image of a fresh `chrona init` starter (the image shows a grey plot with a `WEEKEND` key; the Scene holds 78 `calendar-closed:*` Rects).

1. **Cause.** `_calendar_closures` in `src/chrona/presentation/review/v05_content.py` reads the working days of `project.calendars[project.calendar]`. With no `project.calendar` the working set is empty, so every day is closed, weekdays included. The View's `shading.nonWorking` (default true) then selects every day.
2. **The Spec has no built-in default calendar.** Spec 03 section 11: an object selects a calendar, "otherwise the Project default calendar is used when a calendar is required". Spec 04 section 8: a WorkPeriod lag "requires a calendar", resolved lag calendar, then target calendar, then Project default. Spec 05 section 6: calendars exist only as declared (`calendars:`); the starter template declares none. Spec 05 section 12 (figures) says `E_FIGURE_CALENDAR_UNAVAILABLE` for "working days with no declared or default calendar", and Spec 65 S6 says a working-day amount with no calendar is Core's `E_CALENDAR_REQUIRED`. So the scheduler never assumes a Monday to Friday week: **no declared calendar means no working-day arithmetic, not "no working day"**.
3. **The legend key.** The packaged Detail Profiles (`editorial`, which the starter uses, and `technical-print`) declare a `calendar-closed` legend entry (`Weekend`). It is drawn from `legend_entries`, which Layout uses both to measure the legend slot and to draw it (two callers: `normalize_v05_surface_content` and `render_review`). It is drawn whether or not any closed day is drawn.
4. **Corpus.** Every large example Project declares a default calendar (`aster-ssd`, `attached-milestones`, `controller-z`, `controller-z-ja`, `halcyon-1`, `orion-asic`). The projects without one are the starter template and some `examples/onboarding` lessons; which public slides change is read from the regenerated evidence, not assumed.

Unverified: which public slides change (read after regeneration); whether a Project that names a default calendar absent from `calendars` is rejected earlier (it is treated as "no calendar" here, which matches what the scheduler does with an unresolvable name: a diagnostic, never a shading).

## 2. Literal acceptance

The issue has no checklist; its "Acceptance proposal" is the literal criterion (copied):

1. A synthetic Project without a calendar yields no `calendar-closed` primitive and no weekend legend key, with a Spec statement of the rule.
2. A Project that declares a calendar is unchanged.

Lane requirements: synthetic tests with no `examples/` input; mutation check; starter and public slides regenerate and each changed slide is reviewed against the rule; rendered images read (starter before and after); corpus output is evidence, not an oracle; no corpus datum edited.

## 3. Decision (owner-level, also recorded on the issue)

**Question.** With no declared calendar, does a day count as closed?

| Option | Meaning | Verdict |
| --- | --- | --- |
| A | No calendar means nothing is declared, so nothing is shaded; the legend key for closed days is not drawn when no closed day is drawn | **chosen** |
| B | Shade a defined default calendar (Monday to Friday) | rejected: the Spec defines none, scheduling refuses to assume one (`E_CALENDAR_REQUIRED`), so shading Saturday and Sunday would show a calendar the schedule does not use |
| C | Keep "no working day" | rejected: it is the defect; it contradicts the scheduler, which treats a missing calendar as missing, not as empty |

**Rule.** Closed-day shading derives only from the Project default calendar (`project.calendar`, resolved in `calendars`). With none, there are no closed days and no exception days. A declared calendar with an empty `working_days` list is a declared fact (every day closed) and is unchanged. Shading and scheduling then agree: both use the declared default calendar or neither does. An object-level `calendar` does not shade (the View has no per-object shading; unchanged).

**Legend key.** A legend entry with the role `calendar-closed` is drawn only when the Scene draws a closed-day band, because a key for something that is not on the plot misleads. The one decision point is `legend_entries`, which both the slot measurement and the drawing use, so the legend slot shrinks together with the entry. This also drops the key when a View turns closed-day shading off or a window holds no closed day; that is the same rule (no band, no key), and it changes no declared-calendar Project that shows a closed day.

**How to reverse.** Return the old closed set from `_calendar_closures` for a missing calendar, and pass `True` for the drawn flag.

## 4. Architecture review

- Core is unchanged: the rule is the existing "calendar only when declared" contract, now honoured by the presentation derivation. No schema, View, Theme, Layout or Scene change; the closed set is an input fact (`calendar_closed`) that Layout already treats as optional (an empty tuple draws nothing).
- Responsibility: content normalization owns which Project facts reach Layout, and so owns both the closed set and the entries of the legend list derived from it. Layout still measures and draws one list.
- Diagnostics: none new. Incompatibility: a Project without a calendar loses its grey plot and its `Weekend` key; that is the intended fix, and no declared-calendar output changes.
- Adjacent rules checked: Spec 50 background ranks (an absent `calendarClosed` overlay removes no valid pair), the narrow-scale rule (exceptions only), the #880 plot extent (fewer overlays), and the contrast gate (no closed-day primitive to judge).

## 5. Implementation plan

| Slice | Files | Tests and evidence | Publication |
| --- | --- | --- | --- |
| S0 | this record | none | this PR |
| S1 | `src/chrona/presentation/review/v05_content.py` (no calendar gives no closure; `legend_entries` takes the drawn flag; one shared helper for the closed set), `src/chrona/usecases/render_review.py` (the second legend caller), Spec 05 section 6 and Spec 50 section 3.4 (the rule), a synthetic test | unit tests on the closure set and the legend list; a Scene-level synthetic Project without and with a calendar; mutation check of the new conditions; starter image before and after; regenerated public slides reviewed one by one | one PR, `Refs #893` |
| S2 | `docs/reviews/current/issue-893-...-acceptance-review-...md` | literal rows, exact commit, three-OS run | one PR |

Evidence needed: starter before and after read as images; every changed public slide listed with the reason (a Project without a calendar, or a key with no band) and none changed for another reason; conformance and the starter perceptibility gate pass.
