<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression fixes

[Current plan, design and architecture review](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856).
Specs08/50 own neutral host identity and Layout validation; Spec06 owns the
shared native-surface heading contract. No Scene/adaptor routing or title logic.

## Literal issue acceptance

### Issue #1841

- Source: [Issue1841](https://github.com/tya5/chrona/issues/1841)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | hints validate against the completed host geometry whatever the primitive kind. On the trial input, hinted renders accept the unchanged routes and the time drops (before/after recorded). | not met | [Host tests](../../../tests/unit/chrona/presentation/layout/test_relation_hints.py) and [decoder controls](../../../tests/unit/chrona/usecases/test_previous_scene.py) pass. Published trial12 timing/route acceptance remain under investigation; no performance acceptance claimed. | — |
| 2 | one shared measure/place rounding for every content-width text; a synthetic case for cells and headers. | not met | [Remaining slice](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856); no completed implementation claimed. | — |
| 3 | the title is honoured; the guide example runs on the default preset in the docs tests. | not met | [Spec06 correction](../../specification/06-view-model.md) published before code; implementation/focused actual-SVG and default-preset guide evidence pending. | — |
| 4 | a route segment may not run along a mark's edge (treat edge contact as an obstacle); a synthetic case. | not met | [Remaining slice](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856); no completed implementation claimed. | — |
| 5 | network rank placement keeps unchanged nodes (hint or stable ordering), and row pitch is quantised so rows above an insertion stay byte-identical. | not met | [Remaining slice](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856); no completed implementation claimed. | — |

## Programme-level criteria (optional)

Official generated-artifact audit, PR CI and exact review-containing main
three-OS release remain required. Public trial inputs and generated evidence
are not edited to absorb failures. Parent1841 remains open for every unmet row.
