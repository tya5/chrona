<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression fixes

[Current plan, design and architecture review](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856).
Specs08/50 own neutral host identity and Layout validation; Spec06 owns the
shared native-surface heading contract. No Scene/adaptor routing or title logic.
Row4 tested tree: `867bf5ffe` (including straight-fit source `ba29cef7b`);
Spec50 corrections, including `2b574fe46`, preceded code. Root's command below
passes 753 tests (3722 deselected; ten existing Pillow deprecation warnings).
Actual synthetic curved/metro SVG/PNG output was inspected. Tests retain full
closed-mark/text clearance, centered terminal identity and straight tangents;
fixed blocked/over-limit cases require diagnosed suppression, not vacuous
route-or-suppression success. Independent architecture review found no safety
bypass or geometry leaking beyond Layout.

```sh
.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout tests/unit/chrona/presentation/scene -k 'relation or route or egress' -m 'not corpus' --tb=short
```

PR1849 run39472589340 failed in derived-preview: our universal head-length
minimum rejected a safe short straight connector, forcing an unplaceable
required PDR stub label; missing-artifact reproduction and derived-ready
failures were downstream. The published correction keeps straight marker fit
separate from bend reserves. The focused programme-board render now completes
(write=false reaches the expected Scene-byte mismatch); all24 relations remain,
and the PDR relation's actual SVG attributes and Scene points match the public
base exactly, without stubs. No corpus/Theme or required-label-policy changes.
Fresh official snapshot and exact-main release evidence remain required.

## Literal issue acceptance

### Issue #1841

- Source: [Issue1841](https://github.com/tya5/chrona/issues/1841)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | hints validate against the completed host geometry whatever the primitive kind. On the trial input, hinted renders accept the unchanged routes and the time drops (before/after recorded). | met | [53 host/decoder controls](../../../tests/unit/chrona/usecases/test_previous_scene.py) and [canonical trial audit](https://github.com/tya5/chrona/issues/1841#issuecomment-6296684466): target-b en-US 61.97→7.68s, Yuya ja-JP 61.09→9.95s. 103/102 accepted, 4/5 safely searched, zero unusable; both retain107 routes and accept all101 unchanged prior paths. Root independently verified matching resource and text geometry. | — |
| 2 | one shared measure/place rounding for every content-width text; a synthetic case for cells and headers. | met | [Forward-fit regressions](../../../tests/unit/chrona/presentation/layout/test_table_forward_fit.py) cover fractional headers/cells, hierarchy indent, affixes, wrapping, rotated headers and real one-ULP shortage. Shared demand/admission/budget helpers retain ordinary required/ellipsis policy, without epsilon or column inflation. Focused table batch126 pass; root integration/boundary/heading batch31 pass (overlap). | — |
| 3 | the title is honoured; the guide example runs on the default preset in the docs tests. | met | [Heading tests](../../../tests/integration/test_network_heading_parts.py) assert actual SVG title/subtitle, omitted/independent parts and required-role refusal; [guide test](../../../tests/integration/test_network_view_guide.py) executes the unqualified default-preset commands and checks real SVG/PNG. Focused heading/default-view/guide batch: 92 pass; official PR1844 integration audit is below. | — |
| 4 | a route segment may not run along a mark's edge (treat edge contact as an obstacle); a synthetic case. | met | [Closed-contact tests](../../../tests/unit/chrona/presentation/layout/test_primary_mark_closed_contact.py) cover top/end-face travel, tiny marks, isolated authorized tips and scoped physical corridors. [Selection controls](../../../tests/unit/chrona/presentation/layout/test_outward_relation_selection.py) preserve hint priority, best graph choices, quality/bounds/obstacle checks and cross-pair ranking; normal outward proposals close the missing route domain without relaxed acceptance. Short terminal candidates are rejected, including the preserved [actual head-tangent regression](../../../tests/unit/chrona/presentation/scene/test_relation_rounded_corners.py). Official artifact and exact-main release gates remain required below. | — |
| 5 | network rank placement keeps unchanged nodes (hint or stable ordering), and row pitch is quantised so rows above an insertion stay byte-identical. | met | **By contract**, per [reviewer decision](https://github.com/tya5/chrona/issues/1841#issuecomment-6297232443): retain fractional authored pitch and fill redistribution; rank-demand moves are accepted, without node hints. Clarified in [Spec33 §13.1](../../specification/33-intent-oriented-layout.md#131-content-coherent-table-timeline-allocation-468) and [network stability](../../specification/50-constraint-driven-gantt-surface-quality.md#dependency-network-composition-1727); no code or preset changes. | — |

## Programme-level criteria (optional)

Rows1–3 merged through PR1844 as `f491f8d5ea7bd450e97019a7df07c615443313cf`;
[CI39464378020](https://github.com/tya5/chrona/actions/runs/39464378020) passed
all applicable checks at exact head `1595f0c82bed87e8e063e9f334d1f99f13440ef2`.
The [official109-path audit](https://github.com/tya5/chrona/pull/1844#issuecomment-6296962743)
finds all50 SVGs/all50 Scenes byte-identical; only74 existing inventory source
anchors change. No redundant raster or authored corpus/derived edits.
Exact review-containing main three-OS release remains required. Parent1841
stays open for row4 and the required release evidence.
