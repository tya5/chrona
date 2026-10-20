<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression fixes

[Current plan, design and architecture review](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856).
Specs08/50 own neutral host identity and Layout validation; Spec06 owns the
shared native-surface heading contract. No Scene/adaptor routing or title logic.
Row4 source: `95fadef98`, including exact stub normalization, verified recovery
observation, early impossible-egress rejection, minimum-lead protected search,
completed narrow-span ports and retained provisional label footprints.
Specs30/50 corrections were published before their corresponding source changes.
The latest CLI/routing/Scene batch passes974 tests; impossible end-face corridors
report actual `egress-collision` identities before search. The mark/viewport
batch passes103 tests; narrow spans retain their1px visual floor and use its
completed right edge for the connector, without moving Schedule dates or
authorizing traversal inside an endpoint host. Scene/adapters do not complete ports.
Actual synthetic curved/metro SVG/PNG output was inspected. Tests retain full
closed-mark/text clearance, centered terminal identity and straight tangents;
fixed blocked/over-limit cases require diagnosed suppression, not vacuous
route-or-suppression success. Independent architecture review found no safety
bypass or geometry leaking beyond Layout.

```sh
.venv/bin/python -m pytest -q tests/cli/test_cli_characterization.py tests/unit/chrona/presentation/layout tests/unit/chrona/presentation/scene -k 'cli or relation or route or egress or forward_point' -m 'not corpus' --tb=short
```

Release is **not accepted**. PR1849 CI39477068127 is red; shards1/3 failures
are identified, while shard2 lost its runner before printing a failure summary.
Current controls:77 observer tests;107 observer/tools/recovery tests (overlap);
all11 typed-fields commands; starter0errors;28 corrected synthetic integrations;
19 egress controls; both balloon-tail regressions. All8 Sunday cases now pass;
the previously over-ceiling protected case uses9,743 expansions under the
unchanged86,016 test ceiling. Completed tail edges are reserved before note indices.
[Old-head official snapshot audit](https://github.com/tya5/chrona/pull/1849#issuecomment-6298974541)
records48 changed visual pairs,399 route changes,72 diagnosed halos and optional
text omissions. Actual before/after SVG rasters for HALCYON02/21/22/24 were viewed
with bundled fonts; the PDR path is unchanged. Corrected observation of that
same50-Scene artifact gives0errors/11 recovery infos without rerendering.
[Optional-label disposition](https://github.com/tya5/chrona/issues/1841#issuecomment-6299771283)
keeps quality/contact and route-preservation guards; historical name counts are
not permission to cross a mark. Forward-point admission preserves all31 neutral
relations and all5 left/top/bottom arrivals without backward right entry
(27 focused tests). Optional label omissions have measured retry-footprint
witnesses and truthful count diagnostics; the separate feasible-reservation
control still recovers both names. All9 affected test-fixture SVG/Scenes were
regenerated through this worktree's asserted venv imports, not public derived
paths; the focused materializer/suppression batch passes9 tests. Annotation and
ja-JP before/after SVG rasters were viewed with bundled fonts. PR1849 lists
per-fixture primitive/route/Text counts;4 CLI diagnostic records changed.
Overlapping scratch-path aliases now normalize deterministically, retaining
filename/error-envelope checks. Fresh official SVG/count review and exact-main
three-OS release remain required.

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
