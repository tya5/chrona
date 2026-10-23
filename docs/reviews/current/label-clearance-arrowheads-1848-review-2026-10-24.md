# Relation ink keeps the label gap from member names and note indices (#1848, row "02 adoption")

Reviewer-requested engine work under the #1848 board row "02 adoption"; no new issue. Base: `origin/main` `e317347d3`. Rendering the reviewer branch
`reviewer/halcyon-02-controls` (dev A's comparison controls from #1941 adopted by HALCYON slide 02, `timeline.mark.labelGap` = 8) showed three core
clearance defects. This change states and implements one project-independent rule for all three; it edits no example, preset, design, gallery or
derived file and keeps the reviewer's YAML out of the diff.

## The rule

A completed relation's painted stroke segments and arrowheads, and a note index, keep the shared label gap (Specification 07 `timeline.mark.labelGap`,
default a quarter of the label font size, at least one pixel) from every placed member-name group, on whichever side of its mark the name or index lies.
The text is in [Specification 07](../../specification/07-style-and-theme.md) and [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md)
(Member-name label gap, "Relation ink and note indices keep the label gap").

It is a first-tier preference with an unchanged fallback in each of its three owners, so it never costs a name, a connected route or an index:

| Owner | What changed | Fallback |
| --- | --- | --- |
| Member-name placement (`surface_member_labels.py`, `surface_routes.py`) | a name first takes a clear candidate that also keeps the gap from the relation endpoint ink at its mark: the existing intrinsic footprint and the same footprint led from the port where the connector leaves its whole host (`exposed_endpoint_footprints`) | the unchanged candidate ladder |
| Route search (`surface_routes.py`, `obstacles.py`) | the NORMAL stage is first searched against the names widened by their own gap (`SurfaceObstacle.label_gap`, `SurfaceObstacleIndex.copy(clearance_overrides=...)`), with the existing completed-ink validators (`route_candidate_ink`) | the unchanged NORMAL search, recovery stages, connected-route name yield and paired stubs |
| Note index (`relation_ink_clearance.py`, `surface_annotations.py`) | an index the unchanged ladder places looks for a candidate on its declared sides, sliding at most two em, that also keeps the gap from completed strokes and arrowheads; an index only the relation ink blocks is recovered by the same slide | an index the ladder suppresses for any other reason stays suppressed |

No new quota, scheduler, reorder, search budget, recovery stage or validator waiver; Scene and adapters are unchanged projection.

### Dev A's earlier work (checked first)

`git log` on `origin/wip/issue-1936-controls`, `origin/wip/issue-1936-acceptance` and `origin/checkpoint/dev-a-1936-controls-design`: the only slice-D commit not
in `main`'s history is `52362ddcb` ("validate completed relation terminal ink against retained labels"); its source and tests are already in `main` byte for byte
(applying the patch to `main` is a no-op, so `route_candidate_ink(..., path_commands=...)` and the prepare/reject-style checks are reused as they stand). The
acceptance branch holds only a review document and the checkpoint branch only specification text. Nothing newer than `main` was found to reuse.

## The three defects, measured on the scratch overlay of `reviewer/halcyon-02-controls`

`main` plus the reviewer's slide-02 files in a scratch worktree only (the overlay is not in this change), `labelGap` 8 px. Distances are painted-ink distance
to the member-name text box or note-index box, from the Scene, by [`measure_label_clearance.py`](assets-label-clearance/measure_label_clearance.py)
(full lists: [before](assets-label-clearance/overlay-02-adoption-before-measure.txt), [after](assets-label-clearance/overlay-02-adoption-after-measure.txt)).
Rasters: [before](assets-label-clearance/overlay-02-adoption-before.png), [after](assets-label-clearance/overlay-02-adoption-after.png).

| Defect | Pair (relation ink to box) | Before | After | Gap |
| --- | --- | ---: | ---: | ---: |
| 1 arrowhead left of a name | "Avionics integration +3d", arrowhead / last segment | 2.50 / 0.00 | 47.83 / 11.50 | 8 |
| | "Bus functional test +15d", arrowhead | 3.53 | 11.53 | 8 |
| | "Payload thermal-vacuum +10d", arrowhead / last segment | 2.50 / 0.00 | 10.50 / 8.00 | 8 |
| | "Spacecraft integration", arrowhead / last segment | 2.50 / 0.00 | 10.50 / 8.00 | 8 |
| 2 route against the start of a name | "Mission control software +3d", segment | 0.00 | 11.50 | 8 |
| | "Detector calibration +2d", segment | 0.00 | 11.50 | 8 |
| 3 index against bar end and stub | note index "2", segment / arrowhead (bar end to index box 4.75 > 12.00) | 0.75 / 2.25 | 8.00 / 9.50 | 8 |

Whole slide (all member-name and note-index pairs within gap + 4 px): 56 pairs closer than 8 px before, 14 after, all remaining ones listed in the after file.
Names 26 > 26, paired stubs 0 > 0, note indices 3 > 3 (the third is recovered by the slide rule above, not by a waiver).

Not satisfiable without moving a name, so unchanged by the preference: the dense "Spacecraft bus" rows (pitch 30 px, name height 21.75 px: the channel between two
names is 8.25 px, so a route in it can be at most about 3.6 px from either, never 8) leave "Bus functional test +15d" 1.50 / 3.27 / 5.50 px from three routes, and the
same stacked-row pattern leaves "EMC and RF compatibility", "Launch campaign", "Flight readiness review" and "Pre-ship review" 0.01-7 px from one route each. Closing them needs a name to move, which the board's constraints forbid. The recovered index "3" sits 2.04 px from the head of `rehearsals-launch` and 4.50 px from its stroke (the diamond's four sides are crowded by three routes).

## Per-slide ledger (all 50 public slides, `main` e317347d3 against this change)

Hashes are SHA-256 (first 12 hex) of the materialized SVG and Scene; "before" equals the committed generated evidence for every slide. A changed slide lists
paired-stub fragments, member names (and any name that is gone), note indices, relations whose route changed, and relation-ink/name/index pairs closer than the
Specification 07 fallback gap with the smallest such distance. HALCYON 02, 11, 12, 16, 19 and 21-25 come first. **Result: 36 of 50 slides change; 14 do not
(HALCYON 21-25 included). No stub is introduced (0 > 0 on every slide), no member name is lost (HALCYON 12 gains one), no relation is dropped; HALCYON 19 gains one
note index that route ink had suppressed.** Rasters of every changed slide: `assets-label-clearance/<example>-<slide>-before.png` and `-after.png`.

| slide | SVG before > after | Scene before > after | stubs | member names | note indices | routes changed | pairs inside gap (least px) |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| HALCYON 02 programme-board | `3eeb358b6c18` > `768a92f436e4` | `1c1c49e2fbb9` > `9a2285f56e05` | 0 > 0 | 26 > 26 | 0 > 0 | 8 of 25 | 37 (0.00) > 3 (1.50) |
| HALCYON 11 overlay-briefing | `5376def13527` > `e5fab195b6d7` | `673630febc46` > `db1e441f092d` | 0 > 0 | 22 > 22 | 2 > 2 | 5 of 24 | 44 (0.00) > 15 (1.25) |
| HALCYON 12 glyph-gates | `3292481123f0` > `477232302cdd` | `285057ac737d` > `9a10c842ceee` | 0 > 0 | 23 > 24 | 1 > 1 | 7 of 24 | 50 (0.00) > 21 (0.50) |
| HALCYON 16 gallery-editorial-lanes | `524b088799c9` > `949146892464` | `492c5350e779` > `0d8fa836c313` | 0 > 0 | 26 > 26 | 0 > 0 | 7 of 25 | 32 (0.00) > 6 (1.00) |
| HALCYON 19 gallery-text-compression | `ff301a73df87` > `7046babe3143` | `2a29caab67df` > `df8c1ad8b8cb` | 0 > 0 | 19 > 19 | 1 > 2 | 6 of 24 | 44 (0.00) > 17 (0.50) |
| HALCYON 21 target-b | `6fc347d6435a` unchanged | `c6b8f461b0eb` unchanged | - | - | - | 0 | - |
| HALCYON 22 yuya | `765268337ead` unchanged | `e07f56b4b191` unchanged | - | - | - | 0 | - |
| HALCYON 23 titlecard | `bd89a399ec1f` unchanged | `913aaed57c68` unchanged | - | - | - | 0 | - |
| HALCYON 24 marquee | `df1b0d618a51` unchanged | `aac105ba1545` unchanged | - | - | - | 0 | - |
| HALCYON 25 sunday | `34d1768df0a4` unchanged | `c482f904378b` unchanged | - | - | - | 0 | - |
| HALCYON 01 mission-brief | `39a45a06966e` > `a5500147f2bd` | `2080df4c4e92` > `be055813d479` | 0 > 0 | 16 > 16 | 0 > 0 | 4 of 11 | 12 (0.00) > 3 (1.50) |
| HALCYON 03 launch-campaign | `69fb7d58ebe0` > `6e7e4213417b` | `7fd2d1798364` > `20c8dad654c8` | 0 > 0 | 11 > 11 | 0 > 0 | 0 of 12 | 14 (0.00) > 1 (1.50) |
| HALCYON 04 tvac-slip | `9c6e4445efd0` > `f5422af70ffa` | `83e8eab6c418` > `eb7cdab9eb0d` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 4 | 13 (0.00) > 3 (0.16) |
| HALCYON 05 dependency-network | `552452e30666` unchanged | `fff6d3adab89` unchanged | - | - | - | 0 | - |
| HALCYON 06 flight-readiness | `e6f648203c85` unchanged | `b6394de63c9e` unchanged | - | - | - | 0 | - |
| HALCYON 07 replan-baseline | `a8d87e4c9def` > `96f9f5e81331` | `6388c3b36118` > `0593b704ba00` | 0 > 0 | 7 > 7 | 0 > 0 | 0 of 6 | 10 (0.00) > 0 (-) |
| HALCYON 13 gallery-editorial | `7cf6b2739ba2` unchanged | `8d8d3e539cc4` unchanged | - | - | - | 0 | - |
| HALCYON 15 gallery-image-notes | `b4c06a7797cd` > `c6a7145a4863` | `4f373f8571dd` > `194ca0782077` | 0 > 0 | 0 > 0 | 3 > 3 | 0 of 24 | 3 (0.75) > 0 (-) |
| HALCYON 26 gates | `9db3b2e34f97` unchanged | `0cd205ba16dd` unchanged | - | - | - | 0 | - |
| aster-ssd/overview | `b9d133c7179c` > `3cff372124c8` | `ce0c0baf911b` > `53cfb0fedcb2` | 0 > 0 | 8 > 8 | 0 > 0 | 0 of 1 | 2 (0.00) > 0 (-) |
| chrona-roadmap/roadmap | `3d70bd6c48ae` unchanged | `769e30e09923` unchanged | - | - | - | 0 | - |
| chrona-roadmap/roadmap-marquee | `2efd68398265` unchanged | `ce4ae9019f85` unchanged | - | - | - | 0 | - |
| chrona-roadmap/roadmap-sunday | `db6eea129c44` unchanged | `4491fb3aca1f` unchanged | - | - | - | 0 | - |
| chrona-roadmap/roadmap-titlecard | `2d6a10923d93` unchanged | `2ebff374c40c` unchanged | - | - | - | 0 | - |
| chrona-roadmap/roadmap-yuya | `cee7f5265c85` unchanged | `9c4a73202088` unchanged | - | - | - | 0 | - |
| controller-z-ja/axis-secondary | `35cd8889ce86` > `3aa2665e94db` | `6c3aa4e9e307` > `e81fc8f89b93` | 0 > 0 | 8 > 8 | 0 > 0 | 3 of 7 | 6 (0.00) > 4 (0.00) |
| controller-z-ja/executive | `f039c11f4390` > `f8a28006ea65` | `e52bd4b71dba` > `70e2b26d9455` | 0 > 0 | 8 > 8 | 0 > 0 | 3 of 7 | 6 (0.00) > 4 (0.00) |
| controller-z/annotation-kinds | `b6dc41cb0edb` > `79e4379d69b7` | `84813f9c29c7` > `fc1c74968c22` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/annotation-rounded | `3f4d295ddfdc` > `00ea339499cf` | `930b51529093` > `b95b3dc6405b` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 7 (0.50) > 7 (0.50) |
| controller-z/annotations | `54c47e561098` > `a205e26becdf` | `ccf0293ac95d` > `55057b7aa1e1` | 0 > 0 | 8 > 8 | 2 > 2 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/as-of-foot | `bd4de1805357` > `ddb86457bcce` | `6a71ae0224db` > `d5d2a6b716d1` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/axis-alternating | `e768e9a2f917` > `328b7ea0de5c` | `0140dfcf3d5d` > `4e2b00464264` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/axis-cell-corners | `1a71fdc5f78c` > `7ae9e8be2563` | `cd5ea1815b4a` > `dabf93ccab2a` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/axis-interval-scales | `65d21a14f58b` > `effe3b44630e` | `185a7e02e98f` > `9e53b76a6736` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/baseline-ghosts | `ace90d161c75` > `5bb0837ebb44` | `c3b0aa0f8c1f` > `5f19c83a332a` | 0 > 0 | 14 > 14 | 0 > 0 | 2 of 7 | 7 (1.00) > 6 (0.03) |
| controller-z/capabilities | `af0f17e135da` > `e0ef72554f15` | `bd756a344109` > `bee13f49ea93` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/elevated | `8d33f6a387cf` > `1eaaa3321578` | `304fe623df69` > `3592a53afd2f` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/executive | `ccb6abc55ea1` > `fbd318af97ec` | `c825931b8830` > `220db3cdc6b3` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/group-child-indent | `4f66264bdedc` > `56239e015a07` | `cba4ffad9c1c` > `1e4e2eff71de` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/group-header-runs | `e9f1438a2724` > `552101322e34` | `2582ec6d0dc5` > `0c5af1645705` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/icons | `665a8ea3a501` > `d67d83dfd8ea` | `affef435d342` > `2be27506aeaa` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/in-progress | `6141fcc2e3b9` > `bd083d73c3f9` | `947e5ac08004` > `36cac15c641b` | 0 > 0 | 8 > 8 | 0 > 0 | 2 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/material-icons | `f6ee02a4171e` > `c0379f71e1a1` | `57a04f6447f7` > `8440483f7373` | 0 > 0 | 8 > 8 | 0 > 0 | 2 of 7 | 6 (0.70) > 4 (0.70) |
| controller-z/plan-only | `4e81889c31d3` > `1ca04130f3cc` | `d6e81ca5ed61` > `b176d124f0bc` | 0 > 0 | 3 > 3 | 0 > 0 | 1 of 2 | 1 (1.50) > 0 (-) |
| controller-z/progress-track | `b08c9095b482` > `e77e61d73a57` | `9fc6da7590c6` > `65bc9d306c1d` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/region-frames | `4c2c4bc92a66` > `d227ee529425` | `dce37be00d0d` > `46e67a0a7617` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 8 | 5 (1.50) > 4 (1.50) |
| controller-z/slot-heading | `fe6cca3cd61b` > `379031ba8ee6` | `a318c74b6bc1` > `c4929585de1b` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 7 (0.50) > 7 (0.50) |
| controller-z/surface-glow | `ec2de78f042b` > `c7f3e301f2af` | `910927bf22f2` > `14d98d0d9aee` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/text-roles | `ee0a2a98b8aa` > `2cad7b8a3a7b` | `1b8948b4c59b` > `161a2f3bebd7` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |
| controller-z/viewer-fit | `48f9bdce14ca` > `a99ec89de991` | `60a4cda02dac` > `a3be93875521` | 0 > 0 | 8 > 8 | 0 > 0 | 1 of 7 | 4 (1.50) > 3 (1.50) |

## Evidence and tests

* Synthetic tests (no `examples/`): [`test_label_clearance_arrowheads_1848.py`](../../../tests/integration/test_label_clearance_arrowheads_1848.py) (arrowhead left of a name,
  route against the start of a name, note index beside a bar end and stub, every endpoint pairing, default and declared gap, a dense chain that loses nothing) and
  [`test_obstacle_clearance_overrides.py`](../../../tests/unit/chrona/presentation/layout/test_obstacle_clearance_overrides.py). The first fails on `main` in every defect case and passes here.
* Three existing assertions are adapted because a name or route legitimately moves, not because a rule is waived: `test_hosted_points` accepts the fixed overlap
  completion (a connected route, one stub fewer) as well as paired stubs; `test_declared_relation_search` also disables outward shapes in its negative control
  (names no longer abut the lead, so a shape settles the lane route); `test_surface_route_label_plan_point_repair` accepts the top vertex when the left vertex's head would lie
  within the gap of a name. The four `render-halcyon-*` entries of the CLI characterization golden file are re-recorded for the changed routing counts.
* Public slide changes make the tests that compare against committed generated evidence differ until the derived-sync bot regenerates it (`test_optional_content_identity`,
  `test_font_set_materialize`, `test_shared_design`, `test_render_review`, `test_route_memo_equivalence`, `test_relation_paths_corpus`); they pass on a scratch copy with the evidence regenerated.
* Tools in `assets-label-clearance/`: `render_public_slides.py` (renders all slides without touching `examples/`), `label_clearance_ledger.py` (this ledger),
  `measure_label_clearance.py`, `rasterize.py` (resvg_py with the bundled font directories).
