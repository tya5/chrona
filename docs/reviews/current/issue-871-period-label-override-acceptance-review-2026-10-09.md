<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — View override of a named period's label (#871, reviewer row)

Implementation: [#1253](https://github.com/tya5/chrona/pull/1253) (head `5bf586ae`). A selected period's label object gains an optional `text` (one to eighty characters, `literalCaption`), `periods[].label.text`, added in place to `view-v0.28` (Spec 56 section 3.2; `python -m tools.schema_equivalence --base-rev origin/main`: PASS, additive=1). The label stays an ordinary `period-label` Text; only its content changes, for that View only. Plan: [Status comment](https://github.com/tya5/chrona/issues/871#issuecomment-6068339316).

**Scope.** #871 is an umbrella of optional follow-ups to #582; its issue body says none is an acceptance row of #582. The only literal acceptance in this slice is the reviewer's added row (2026-10-08). The eight numbered follow-ups (period variants, edge treatments, a period legend entry, date offsets, terse syntax, bundled-preset roles, contrast through a translucent host, derived figures) are out of scope here and untouched: they are not in this review's table, and #871 stays open as their owner issue (variants and edge treatments are dev A / decoration areas; the legend entry is #497; presets are #718; figures are #586). The Marquee adoption row is an `examples/**` View edit, the reviewer's step.

## Literal issue acceptance

### Issue #871

- Source: [Issue #871 reviewer row](https://github.com/tya5/chrona/issues/871)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The View override sets the period-label text. | met | [Diff](https://github.com/tya5/chrona/pull/1253/files): `schemas/view-v0.28.schema.yaml` `periods[].label.text`, `ViewPeriod.label_text`, `render_review._selected_periods`, Spec 06; test `test_a_view_label_text_replaces_the_project_period_title_for_that_view_only` in `tests/integration/test_named_periods.py` (label text `OPENING NIGHT` against the Project title `window`); schema bounds in `test_the_label_text_follows_the_literal_caption_rule`. | — |
| 2 | Absent an override, the output is byte-identical. | met | [PR body](https://github.com/tya5/chrona/pull/1253): no corpus View declares `label.text` and the unmodified path is unchanged; the 56 existing named-period tests pass unchanged; `test_without_a_label_text_the_output_is_byte_identical`. | — |
| 3 | Marquee adopts it. | deferred | Adoption is a View edit in [`examples/halcyon-1/views/24-marquee.yaml`](../../../examples/halcyon-1/views/24-marquee.yaml) (add `text: OPENING NIGHT` to the `launch-window` period label), and `examples/**` is reviewer-owned; the schema, contract and Layout path are ready. | [Owner note on the issue](https://github.com/tya5/chrona/issues/871#issuecomment-6068339316): the reviewer adds `label.text` to the Marquee View and regenerates the evidence with derived-sync. |

## Programme-level criteria (optional)

None.
