<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression fixes

[Current plan, design and architecture review](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856).
Specs08/50 own neutral host identity and Layout validation; Spec06 owns the
shared native-surface heading contract. No Scene/adaptor routing or title logic.
Row4 source: `fd281bb6a` with shared lead geometry `66f65dac3` and tests
`948cca641`/`a7e93c9b1`/`8c3a20061`; Spec50 corrections preceded code.
Root focused runs: 114 shape/contact/style/reduction/egress/quality tests,
107 hint/search/resolution/policy tests, and 24 terminal/contact tests pass
(overlap). Actual synthetic SVG/PNG curved and metro output was inspected;
closed-mark/text clearance and terminal tangents remain asserted. Independent
architecture review found no safety bypass or geometry leaking beyond Layout.

## Literal issue acceptance

### Issue #1841

- Source: [Issue1841](https://github.com/tya5/chrona/issues/1841)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | hints validate against the completed host geometry whatever the primitive kind. On the trial input, hinted renders accept the unchanged routes and the time drops (before/after recorded). | met | [53 host/decoder controls](../../../tests/unit/chrona/usecases/test_previous_scene.py) and [canonical trial audit](https://github.com/tya5/chrona/issues/1841#issuecomment-6296684466): target-b en-US 61.97→7.68s, Yuya ja-JP 61.09→9.95s. 103/102 accepted, 4/5 safely searched, zero unusable; both retain107 routes and accept all101 unchanged prior paths. Root independently verified matching resource and text geometry. | — |
| 2 | one shared measure/place rounding for every content-width text; a synthetic case for cells and headers. | met | [Forward-fit regressions](../../../tests/unit/chrona/presentation/layout/test_table_forward_fit.py) cover fractional headers/cells, hierarchy indent, affixes, wrapping, rotated headers and real one-ULP shortage. Shared demand/admission/budget helpers retain ordinary required/ellipsis policy, without epsilon or column inflation. Focused table batch126 pass; root integration/boundary/heading batch31 pass (overlap). | — |
| 3 | the title is honoured; the guide example runs on the default preset in the docs tests. | met | [Heading tests](../../../tests/integration/test_network_heading_parts.py) assert actual SVG title/subtitle, omitted/independent parts and required-role refusal; [guide test](../../../tests/integration/test_network_view_guide.py) executes the unqualified default-preset commands and checks real SVG/PNG. Focused heading/default-view/guide batch: 92 pass; official integration artifact and release gates remain pending. | — |
| 4 | a route segment may not run along a mark's edge (treat edge contact as an obstacle); a synthetic case. | met | [Closed-contact tests](../../../tests/unit/chrona/presentation/layout/test_primary_mark_closed_contact.py) cover top/end-face travel, tiny marks, isolated authorized tips and scoped physical corridors. [Selection controls](../../../tests/unit/chrona/presentation/layout/test_outward_relation_selection.py) preserve hint priority, best graph choices, quality/bounds/obstacle checks and cross-pair ranking; normal outward proposals close the missing route domain without relaxed acceptance. Short terminal candidates are rejected, including the preserved [actual head-tangent regression](../../../tests/unit/chrona/presentation/scene/test_relation_rounded_corners.py). Official artifact and exact-main release gates remain required below. | — |
| 5 | network rank placement keeps unchanged nodes (hint or stable ordering), and row pitch is quantised so rows above an insertion stay byte-identical. | not met | [Remaining slice](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856); no completed implementation claimed. | — |

## Programme-level criteria (optional)

Official generated-artifact audit, PR CI and exact review-containing main
three-OS release remain required. Public trial inputs and generated evidence
are not edited to absorb failures. Parent1841 remains open for every unmet row.
