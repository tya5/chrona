<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #1628, #1629, #1630

Observed on `main` at `cd4dae681`. Criteria are copied from the issue bodies and every comment fetched on 2026-10-17 (`gh issue view N --comments`, latest comment on #1628 at 08:16 UTC). Checks were run in a fresh virtual environment with the package, `chrona-fonts-noto-cjk` and `resvg_py` installed editable, as `.github/workflows/conformance.yml` does. Trial inputs come from branch `reviewer/trial3-inputs` (`trial3/project.yaml`), rendered to PNG with `wallboard-dark`, `target-b`, `technical-print` and `sunday` and viewed. Closure waits for a green three-OS run on main containing this review.

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #1628 | [#1639](https://github.com/tya5/chrona/pull/1639) (categorical scales never repeat a hue; remainder folds into `Other`), [#1643](https://github.com/tya5/chrona/pull/1643) (a folded tint scale takes a readable neutral ground) | none; the reviewer YAML PR announced in the post-review was withdrawn by the owner decision below |
| #1629 | [#1636](https://github.com/tya5/chrona/pull/1636) (group-header label bounded to its table-bounded band), [#1638](https://github.com/tya5/chrona/pull/1638) (`initials` abbreviates only multi-word names) | none |
| #1630 | [#1640](https://github.com/tya5/chrona/pull/1640) | none |

Related, not rows: [#1633](https://github.com/tya5/chrona/issues/1633) (smaller items split from #1629, open) and [#1632](https://github.com/tya5/chrona/issues/1632) (sunday route search on a chained plan, fixed by [#1644](https://github.com/tya5/chrona/pull/1644)).

## Literal issue acceptance

### Issue #1628

- Source: [Issue #1628](https://github.com/tya5/chrona/issues/1628)
- Observed: 2026-10-17

Comment record that shapes the rows: the reviewer post-review (target-b fold regression, and "Planned and Milestone still share one legend swatch ... the legend fix needs the YAML you listed (more `series-N` and a `gate` fill)"), then the [owner decision](https://github.com/tya5/chrona/issues/1628#issuecomment-6231589140) (wallboard-dark keeps six `series-1`..`series-6` colours, scheme.yaml unchanged, no reviewer palette change follows), then the [reviewer post-review on `cd4dae681`](https://github.com/tya5/chrona/issues/1628#issuecomment-6231630756) (target-b regression fixed; palette stays; "remaining for closure: dev B's literal acceptance review").

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic test: N+1 categories on an N-colour palette → N distinct hues plus a neutral "Other", no hue shared with Planned/Milestone, and the diagnostic. | met | [`test_n_plus_one_values_give_n_distinct_hues_and_one_neutral_other`, `test_the_remainder_folds_in_source_order_into_a_single_entry`, `test_a_palette_colour_reserved_by_planned_or_milestone_is_never_assigned`](../../../tests/unit/chrona/presentation/model/test_color_scale_distinct_hues.py) and [`test_wallboard_dark_legend_has_no_two_entries_with_one_colour`](../../../tests/integration/test_categorical_hues_not_cycled.py) pass on this base. The diagnostic is `I_PRESENTATION_SCALE_FOLDED`; on the trial it reports `distinctColors` 5, `foldedCount` 4 (`Ken`, `鈴木`, `Lena`, `QA team`). The tint variant added by [#1643](https://github.com/tya5/chrona/pull/1643) is covered by [`test_a_folded_tint_group_keeps_its_header_text_readable`](../../../tests/integration/test_group_tint.py). Rule stated in [Spec 60](../../specification/60-declared-colour-scales.md). | — |
| 2 | On the trial CSV, wallboard-dark's legend shows no two entries with the same colour, viewed as PNG. | narrowed | Narrowed by the reviewer in [this disposition](https://github.com/tya5/chrona/issues/1628#issuecomment-6231703249): the row now reads that no two owner entries share a colour and no owner colour equals the Planned/Milestone key; the Planned and Milestone kind keys may share their colour (the Milestone key is a miniature of the planned point, #499). Evidence as originally observed: trial `project.yaml` rendered with `--preset wallboard-dark` and viewed; owner entries distinct (`pm` #2A9D43, `佐藤` #D2691E, `Raj` #8957E5, `Mika` #D1478C, `田中` #1B9AAA, `Other` #69727D), `W_PRESENTATION_SCALE_NOT_SEPARABLE` gone, `legend-swatch:planned` and `legend-swatch:milestone` both `#2F81F7` (allowed by the narrowed row). The reviewer tried and rejected a `gate` YAML fix (it whitens every milestone and raises `W_SCENE_MARK_CONTRAST` on halcyon-1). | The reviewer's [disposition comment on #1628](https://github.com/tya5/chrona/issues/1628#issuecomment-6231703249) amends the row; it is the reviewer's own criterion, so no owner amendment is needed. |
| 3 | Public SVG/Scene changes listed with counts. | met | `python tools/regenerate_public_examples.py --check --jobs 4` on this base prints `Public materializers: PASS (50 slides)`. Counts are in the PR tables: [#1639](https://github.com/tya5/chrona/pull/1639) 0 public slides changed, 0 fixture Scenes changed; [#1643](https://github.com/tya5/chrona/pull/1643) 0 public changes. | — |

Reviewer-found regression (a comment, not a row): target-b folded owners drew a dark band with unreadable header text. Fixed in [#1643](https://github.com/tya5/chrona/pull/1643); on this base the trial on target-b (viewed) shows `pm`, `佐藤`, `田中`, `鈴木` on one light grey-blue band with dark readable headers, and the diagnostics hold only `I_PRESENTATION_SCALE_FOLDED`, `I_VIEW_FIELD_ROLE_UNBOUND` and `I_LAYOUT_RELATION_POLICY_SUPERSEDED` (no `W_SCENE_STATE_TEXT_CONTRAST`). This agrees with the reviewer's post-review on `cd4dae681`.

### Issue #1629

- Source: [Issue #1629](https://github.com/tya5/chrona/issues/1629)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; synthetic twins for the column fit and the CJK panel heading. | met | The [trace comment](https://github.com/tya5/chrona/issues/1629) (technical-print `transform: initials`; sunday label unbounded when a header has no tab) is on the issue. Twins pass on this base: [`test_owner_cell_is_whole_and_inside_the_table`](../../../tests/integration/test_owner_column_fit_1629.py) (Latin and CJK) and [`test_long_header_label_ellipsises_inside_its_band` / `test_short_header_label_is_shown_whole_inside_its_band`](../../../tests/integration/test_group_header_text_bounded_1629.py) (Latin and CJK). Rule in [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md), "Text-sized header bands". | — |
| 2 | On the trial CSV, technical-print shows full owner names and sunday shows full panel names inside their boxes, viewed as PNG. | narrowed | Viewed on this base. technical-print shows `pm`, `佐藤`, `Raj`, `Mika`, `Ken`, `Lena`, `田中`, `鈴木` whole (the original cut to "P", "佐", "R" is gone) and `QA team` as `QT`. sunday shows all ten panel names inside their boxes, none running past; the trailing `…` in "IN THE KEN…" is the heading template's own literal (trace on the issue). The `QT` for the two-word `QA team` follows the [reviewer decision](https://github.com/tya5/chrona/issues/1629): keep `transform: initials` and abbreviate only names of two or more words, so "full owner names" holds for every one-word owner and a multi-word owner reads as initials by that decision. Rule in [Spec 46](../../specification/46-halcyon-resource-authoring.md) (Cell transform), tested by [`test_the_initials_rule`](../../../tests/integration/test_initials_cell_transform.py). The row text was not edited after the decision. | The reviewer's decision comment on [#1629](https://github.com/tya5/chrona/issues/1629) amends the row; the reviewer has stated that no owner confirmation is needed (names the literal row, links the same decision). |
| 3 | Public SVG/Scene changes listed with counts. | met | `regenerate_public_examples.py --check --jobs 4`: `PASS (50 slides)`. [PR #1636](https://github.com/tya5/chrona/pull/1636) and [PR #1638](https://github.com/tya5/chrona/pull/1638) each list 0 SVG and 0 Scene changes (no committed example uses technical-print or `transform: initials`). | — |

Smaller items (empty October column, empty band under the chart, editorial "Lane" label) are not rows; they are tracked in the open [#1633](https://github.com/tya5/chrona/issues/1633). [#1632](https://github.com/tya5/chrona/issues/1632) (found while tracing) was fixed separately by [#1644](https://github.com/tya5/chrona/pull/1644) and is not part of this review.

### Issue #1630

- Source: [Issue #1630](https://github.com/tya5/chrona/issues/1630)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | SKILL.md states where diagnostics appear, matching the CLI; PDF rendering writes no non-JSON noise to stderr (test). | met | [SKILL.md](../../../skills/chrona/SKILL.md) "Warnings and diagnostics": a JSON object on standard output with a `warnings` array, standard error empty. On the trial, `chrona render --preset technical-print --output tp.pdf` leaves stderr at 0 bytes. Test: [`test_pdf_render_writes_nothing_to_stderr_and_json_to_stdout`](../../../tests/cli/test_cli_trial3_gaps.py) (subprocess). | — |
| 2 | `import --help` names the columns or links the guide; the skill has a short CSV section including `--role` and its effect. | met | `chrona import --help` lists the columns (`id`, `title`, `type`, `start`, `end`, `finish`, `duration`, `parent`, `predecessors`, `deadline`, `calendar`, `progress`, `actual_start`, `actual_finish`) and names [csv-import](../../guides/csv-import.md). [SKILL.md](../../../skills/chrona/SKILL.md) has the CSV paragraph with `--role responsible=team` and the lane-grouping effect. Test: [`test_import_help_names_the_columns_and_the_guide`](../../../tests/cli/test_cli_trial3_gaps.py). | — |
| 3 | `validate` accepts an Actual Set file or gives a diagnostic naming the right command (test). | met | `chrona validate skills/chrona/examples/actual.yaml` prints `{"status": "ok", "diagnostics": [], "resource": "actual-set"}`. Tests: [`test_validate_accepts_an_actual_set_by_its_kind`, `test_validate_rejects_a_bad_actual_set_with_its_own_diagnostic`, `test_validate_names_the_missing_part_of_an_actual_set`](../../../tests/cli/test_cli_trial3_gaps.py). | — |
| 4 | The skill mentions `.typ` output, and the warning is explained or removed. | met | [SKILL.md](../../../skills/chrona/SKILL.md) names `.typ` (installed font family) and explains `W_VIEWER_FIT_NOT_HONOURED`; the code is kept and explained in [diagnostics.md](../../../skills/chrona/references/diagnostics.md). `chrona render --preset sunday --output s.typ` still emits the warning, as documented. | — |

## Programme-level criteria (optional)

| Issue | Fully met | Open rows |
| --- | --- | --- |
| #1628 | 1, 2 (as narrowed), 3 | none |
| #1629 | 1, 3 | 2 (narrowed by the reviewer decision) |
| #1630 | 1, 2, 3, 4 | none |

Public side effects of the five PRs, from their tables and this base's `regenerate_public_examples.py --check` (PASS, 50 slides):

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| Public examples (50 slides) | 0 | 0 | 0 | 0 |
| Fixture Scenes | 0 | 0 | 0 | 0 |
| This review (docs only) | 0 | 0 | 0 | 0 |

## Architecture conclusion

#1628 sits in the presentation colour-scale rule (Spec 60) with the use-dependent fold colour in the Scheme resolution; no preset YAML changed. #1629 is one Layout rule for header labels plus the View cell transform rule; Owner column fit was a preset declaration the reviewer chose to keep. #1630 is CLI, skill text and the PDF font logging only. #1630 meets every literal row and may close after a green three-OS run containing this review. #1629 may close after a green three-OS run containing this review (row 2 is narrowed by the reviewer's `initials` decision, which needs no owner confirmation). #1628 meets every row (row 2 as narrowed by the reviewer) and may close after the same run.
