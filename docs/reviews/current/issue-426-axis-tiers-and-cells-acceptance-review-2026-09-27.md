<!-- chrona:literal-acceptance/v1 -->

# Release Review — Axis Tier Appearance, Lanes, Cells and Rule (#426)

**Supersedes:** the [rows 1–4 review](issue-426-axis-tier-appearance-acceptance-review-2026-09-27.md), which predates the issue body's extension to ten rows. **Reviewed product:**
- I426-1: `b36a0a14` (View v0.24), `b7e29fdc` (lanes and appearance), `42defba5` (evidence), [slice review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md);
- I426-2: `866190d1` (lanes, cells, rule and inset; presets).

**Design:** [design](../../design/issue-426-axis-tier-appearance-design-2026-09-26.md), [correction for rows 5–10](../../design/issue-426-axis-cells-correction-2026-09-27.md), [review](issue-426-axis-cells-correction-architecture-review-2026-09-27.md). This review also serves as the I426-2 slice review.

## I426-2 evidence

- **Theme v0.11 (in place):** `laneBlockSize`, `cellGap` and `labelInset`, plus the roles `axis-cell-separator` and `axis-rule`. The registry gains `axisRule` and `axisCellSeparator`. Without the declarations nothing changes: `--check` of the 25 slides was byte-identical before the Theme edits.
- **Every shipped Theme binds `axis-rule`:** 12 corpus Themes plus 5 bundle Themes; the two derived Themes inherit it and re-pin their base. The public batch adds exactly one `axis-rule` primitive to each of the 23 timeline slides, and changes nothing else. The two network slides are unchanged.
- **The five presets:**
  - quarter and month band tiers and label tiers paired by `typographyRole`;
  - 24 px and 22 px declared lanes (the axis metric raised to 46);
  - 2 px cell gaps, separators, the axis rule, and a 0.5 em month inset.
- **Tests:** [`test_axis_cells.py`](../../../tests/integration/test_axis_cells.py) covers every preset against HALCYON-1:
  - two lanes stacked from the axis top;
  - each band fills its lane and each label box is centred in it;
  - gaps between cells, separators, and the rule at the axis bottom;
  - the month inset;
  - the rule on every committed timeline slide.
- **Checks:** full `pytest` 1265 passed, 23 skipped; conformance PASS.
- **Visual check:** PNG crops of the `mission-light`, `control-room-dark`, `print-mono` and `executive-light` axes show bounded quarter and month cells with centred labels.
- **Limitation, recorded:** the axis slot's height comes from the Theme metric `timeline.axis.blockSize`. A Theme declaring lanes must size it to at least the lane total; otherwise the labels report `W_LAYOUT_LABEL_OVERFLOW`, as they do today, rather than growing the slot.

## Literal issue acceptance

### Issue #426

- Source: [Issue #426](https://github.com/tya5/chrona/issues/426)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A view can declare two `band` tiers and both render, each in its own lane, neither covering the other. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md). | — |
| 2 | Two band tiers can take different fills from the Theme. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md). | — |
| 3 | Two labels tiers can take different sizes, weights and colours. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md). | — |
| 4 | One committed example renders a two-tier date band whose tiers are visually distinct, and reproduces byte-identically. | met | Controller Z `axis-tiers` ([manifest](../../../examples/controller-z/manifest.yaml)). | — |
| 5 | A labels tier has a declared block size (its lane), and its label is **vertically centred** in that lane; the band of the same tier fills exactly that lane. | met | `laneBlockSize`; [centred-label and band-in-lane test](../../../tests/integration/test_axis_cells.py). | — |
| 6 | A tier can draw **cell boundaries**: at least a separator rule between intervals within the axis and a per-cell gap. A per-cell outline is also desirable. | met | `axis-cell-separator` and `cellGap` ([test](../../../tests/integration/test_axis_cells.py)); per-cell outline via the existing `backgroundTreatment: outline`. | — |
| 7 | The axis can draw a **rule at its boundary with the plot**, and the shipped Themes do so by default. | met | `axis-rule` bound in all 17 shipped Themes; [committed-slide test](../../../tests/integration/test_axis_cells.py). | — |
| 8 | A start-aligned label has a Theme-declared **inset** from its cell edge. | met | `labelInset`; [inset test](../../../tests/integration/test_axis_cells.py). | — |
| 9 | The five catalogue presets (#470) use lanes, centring, cell boundaries and the axis rule. Their HALCYON-1 axis shows quarters and months as distinct, bounded cells with centred labels. | met | [Preset test, parametrized over all five](../../../tests/integration/test_axis_cells.py); PNG check above. | — |
| 10 | The optional expectations (alternating fills, corner shape, ticks, two labels per cell) are either delivered or filed as follow-ups with the targets that ask for them. | met | Filed with their targets: [#490](https://github.com/tya5/chrona/issues/490) alternating and per-interval fills, [#491](https://github.com/tya5/chrona/issues/491) corner shape, [#492](https://github.com/tya5/chrona/issues/492) ticks, [#493](https://github.com/tya5/chrona/issues/493) two labels per cell. | — |

## Programme-level criteria (optional)

- CI: [four-job CI run](https://github.com/tya5/chrona/actions/runs/36265143691) on `866190d1`, green. (Note: `866190d1` also carried the #429/#383 agent's design document and Specification 62 addendum, staged in the shared checkout by mistake; their content is unaffected.)

## Architecture conclusion

- The Theme declares; Layout completes lanes, centring, insets, cells, separators and the rule; Scene projects Paths and Rects; the adapters are unchanged.
- No View version was needed for rows 5–10.

Release disposition: all ten rows met.
