<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — View override of a named period's label (#871, reviewer row)

Implementation: [#1253](https://github.com/tya5/chrona/pull/1253) (head `5bf586ae`). A selected period's label object gains an optional `text` (one to eighty characters, `literalCaption`), `periods[].label.text`, added in place to `view-v0.28` (Spec 56 section 3.2; `python -m tools.schema_equivalence --base-rev origin/main`: PASS, additive=1). The label stays an ordinary `period-label` Text; only its content changes, for that View only. Plan: [Status comment](https://github.com/tya5/chrona/issues/871#issuecomment-6068339316).

**Scope.** The board selects issue-body follow-ups 1–3 (variants, edges, period legend entries); optional items 4–8 are unselected. All selected follow-ups and the three unchanged literal criteria below are met on published READY6e955ada.

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

| Selected follow-up | Evidence | Release state |
| --- | --- | --- |
| 1. Period variants | [PR1486](https://github.com/tya5/chrona/pull/1486); 158 focused tests; all92 public Scene/SVG bytes unchanged | Exact READY7a08f0c0 [three-OS release38506567088](https://github.com/tya5/chrona/actions/runs/38506567088) passed |
| 2. Edge treatments | [Synthetic Scene/SVG tests](../../../tests/integration/test_named_period_edges.py): single/double rules, fit refusal, injective IDs, pattern pigments, outline/none, overlap ranks; [channel tests](../../../tests/unit/chrona/presentation/scene/test_shape_paint_channels.py) | met; PR1488 and common release gate below |
| 3. Period legend entries | [Public source-legend tests](../../../tests/integration/test_period_legend_source.py): same-role independent identities, source/role pointers, absent background/slot, wording, base/variant catalogue-pattern fidelity | met; PR1488 and common release gate below |

[PR1488](https://github.com/tya5/chrona/pull/1488) merged36085747. Exact-main
[release38513826857](https://github.com/tya5/chrona/actions/runs/38513826857)
passed on6e955ada73b490652f92ba3913f957fe65c9e69d, containing this acceptance
review and all selected implementations: Windows/macOS/Ubuntu full pytest,
conformance and wheel/smoke, MCP and newest-Python public materializers succeed.
Final artifact11870002491 preserves all92 public Scene/SVG bytes; only three
intended generated reports change. Focused224 and migration154 tests pass.

## Architecture review

The [completed work record](../planning/issue-871-period-role-variants-2026-10-14.md)
links the pre-code published contracts. Layout completes geometry and identities;
Scene consumes transient channel intent without adapter inference. Catalogue ink
belongs to fill content, not the host outline. Legacy glyph precedence and omitted
fields remain unchanged. Root independently caught and corrected base/variant
legend pattern admission; no project-specific branch or example change was added.
Schema equivalence passes (additive2/equal36; five known baseline-invalid documents).
The CI-owned snapshot and published derived commit resolve report staleness;
no report or example was hand-patched. Renderer review confirms catalogue tiles
retain their own stroke geometry, with no patterned host outline in SVG/PNG/PDF
or Typst/TikZ. The transient channel mask is consumed before Scene serialization.
