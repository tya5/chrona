<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — View override of a named period's label (#871, reviewer row)

Implementation: [#1253](https://github.com/tya5/chrona/pull/1253) (head `5bf586ae`). A selected period's label object gains an optional `text` (one to eighty characters, `literalCaption`), `periods[].label.text`, added in place to `view-v0.28` (Spec 56 section 3.2; `python -m tools.schema_equivalence --base-rev origin/main`: PASS, additive=1). The label stays an ordinary `period-label` Text; only its content changes, for that View only. Plan: [Status comment](https://github.com/tya5/chrona/issues/871#issuecomment-6068339316).

**Scope.** #871 is an umbrella of optional follow-ups to #582; its issue body says none is an acceptance row of #582. The only literal acceptance in this review's table is the reviewer's added row (2026-10-08). The Marquee adoption remains reviewer-owned corpus work and is now met on `main`. Separately, this update records local implementation evidence for optional follow-up 1 (period variants); it does not add an acceptance row or close #871. Edge treatments and a period legend entry remain unimplemented and separately designed follow-ups; the other numbered items are untouched. #871 remains open for the selected successor work.

## Literal issue acceptance

### Issue #871

- Source: [Issue #871 reviewer row](https://github.com/tya5/chrona/issues/871)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The View override sets the period-label text. | met | [Diff](https://github.com/tya5/chrona/pull/1253/files): `schemas/view-v0.28.schema.yaml` `periods[].label.text`, `ViewPeriod.label_text`, `render_review._selected_periods`, Spec 06; test `test_a_view_label_text_replaces_the_project_period_title_for_that_view_only` in `tests/integration/test_named_periods.py` (label text `OPENING NIGHT` against the Project title `window`); schema bounds in `test_the_label_text_follows_the_literal_caption_rule`. | — |
| 2 | Absent an override, the output is byte-identical. | met | [PR body](https://github.com/tya5/chrona/pull/1253): no corpus View declares `label.text` and the unmodified path is unchanged; the 56 existing named-period tests pass unchanged; `test_without_a_label_text_the_output_is_byte_identical`. | — |
| 3 | Marquee adopts it. | met | The [Marquee View](../../../examples/halcyon-1/views/24-marquee.yaml) now declares `text: OPENING NIGHT`; the generated [Scene](../../../examples/halcyon-1/generated/24-marquee.scene.json) and [SVG](../../../examples/halcyon-1/generated/24-marquee.svg) contain `period-label:launch-window` with that text. [Adoption PR #1260](https://github.com/tya5/chrona/pull/1260). | — |

## Programme-level criteria (optional)

None.

## Optional follow-up 1 — period variants (partial implementation; no closure)

The approved [variant plan](../../planning/active/issue-871-period-role-variants-2026-10-14.md)
selects only the common-slug View variant and its paired band/label role families.
Local implementation commit `1ab5febc` adds selected-role propagation and focused
synthetic evidence. The 158-test focused batch passes; it proves simultaneous
variants with distinct band fill/opacity/order and label font-size/letter-spacing,
completed bounds/baseline/TextLayout, contrast treatment, pattern admission,
collision checks, capability closure, exact unsupported-property pointers,
unchanged unvaried output, and required-role timing. Schema L1 against
`origin/main` passes (`additive=1, equal=37`). The schema-delta ledger cleanup
retired six mechanically proven stale #1341 L1 records; its pruner limitation and
the exact proof are recorded in the active plan. Final CI and public-derived
artifact review for the variant implementation remain pending publication.

This partial evidence does not cover edge treatments or period legend entries;
both remain unimplemented follow-ups. It does not close #871.
