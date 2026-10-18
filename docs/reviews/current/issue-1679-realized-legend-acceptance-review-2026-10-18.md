# Issue 1679 — realized legend acceptance

<!-- chrona:literal-acceptance/v1 -->

Implementation source `a7fc836ac8f386be589bc86fd20ee632152db71c`, based on
`0c81797404e3af616c0ae08e9b07ffc8ad21e767`. [Current design/plan](../../planning/active/issue-1679-realized-legend-work-record-2026-10-18.md).
Official derived snapshot [CI39090738185](https://github.com/tya5/chrona/actions/runs/39090738185)
provides the 50-slide table below. Snapshot generation, MCP and reproduction
pass; conformance fails on the legend checker's stale multipart/Progress rules
(15 findings), and the three pytest shards failed12/12/10 tests. Checker
alignment now passes32 unit/7 native tests and the archived official50 Scenes
with zero findings. Source-identity/error/fixture corrections and explicit
legend-role visual fanout pass focused regression batches; the next exact-head
CI must verify them. No failed gate is treated as acceptance.
Supplemental Sunday, Gates and glyph-gates PNGs were inspected; their input SVGs
are byte-identical to the official artifact. The artifact shows Sunday's seven expected
keys without overflow and Gates’ five keys without a viewport warning. It adds
two Yuya progress-swatch contrast warnings; no glyph-gates strict contrast
errors or source-YAML repairs. Keep the issue open pending exact-head CI and
exact-main release evidence.

## Literal issue acceptance

### Issue #1679

- Source: [Issue #1679](https://github.com/tya5/chrona/issues/1679)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A synthetic project with actuals, rendered with executive-light: every distinct realized mark paint has exactly one legend key, and the actual and progress keys use the realized paints. | met | [Native/SVG tests](../../../tests/integration/test_realized_legends.py) cover scalar paints, exact Progress paint and one composite key per complete ordered glyph. The dark-canvas synthetic fixture passes strict contrast. Official snapshot `a7fc836ac8f386be589bc86fd20ee632152db71c` has the realized glyph-gates keys and no glyph-gates strict contrast errors; two Yuya progress-swatch contrast warnings remain reported, not suppressed. | — |
| 2 | When an encoding replaces the planned paint on every planned mark, no base planned swatch remains; the encoding's entries stand in its place. A mixed case (some planned marks unencoded) keeps the base key. | met | [Native encoding tests](../../../tests/integration/test_realized_legends.py): all-covered View encoding removes Planned; selective Style encoding retains the unencoded base witness. Existing scoped-legend and finite-swatch tests retain their geometry/paint assertions. | — |
| 3 | target-b without snapshot or actual has no baseline, actual or in-progress keys and no empty Δ column. | met | [Pinned trial5](https://github.com/tya5/chrona/tree/9fa6062de/trial-5) target-b native PNG/Scene inspected: unavailable keys and Δ cells/header removed. Native synthetic absent/supplied-empty and Snapshot-only tests retain source-presence distinctions. | — |
| 4 | A count table of the public example changes, and the PNGs checked. | met | [Official snapshot](https://github.com/tya5/chrona/actions/runs/39090738185), source `a7fc836ac`, base `0c8179740`; all50 Scene slides counted below. Inspected supplemental Sunday (`7ade16309f14ef9df042875a71a555075f980b57ead6fd9c68493f32f26f0554`), Gates (`8c13abe5f30903f34efbfebd5362012760b7ffaf23fd7f45516b99dc72982ee1`) and glyph (`187866160bad64b1ef2a3ac57e86b339a656698b10ac5d3364a29c6cb7a8ca03`) PNGs; their input SVGs are byte-identical to official artifacts. | — |

## Programme-level criteria (optional)

## Public count table

Official snapshot source: `a7fc836ac8f386be589bc86fd20ee632152db71c`; base:
`0c81797404e3af616c0ae08e9b07ffc8ad21e767`. Counts are added/removed/changed
**by Scene primitive ID**; text counts are a subset. Across 50 slides: 160 / 168
/ 189 total primitive changes, of which 160 / 168 / 164 are legend primitives.
There are 25 changed nonlegend primitives, all Text placement/bounds changes;
no nonlegend primitive was added or removed, and no text content changed.
There are zero actual dependency-route changes. Twelve changed dependency
entries are the `legend-swatch:dependency` line-key positions, not routes. Two
new diagnostics are Yuya progress-swatch `W_SCENE_MARK_CONTRAST` warnings.
No source YAML or canonical generated output was edited.
Snapshot inventory:42 SVGs and43 Scenes change; overlay-briefing changes only
Scene metadata, hence its zero primitive row. Three derived Markdown reports
change; the semantic-realization report is byte-identical to baseline.

| Slide | Primitives +/−/~ | Text +/−/~ | New diagnostics |
| --- | --- | --- | --- |
| aster-ssd/overview | 2/2/0 | 1/1/0 | — |
| chrona-roadmap/roadmap | 2/6/7 | 1/3/3 | — |
| chrona-roadmap/roadmap-yuya | 4/7/12 | 2/3/3 | contrast×1 |
| chrona-roadmap/roadmap-titlecard | 4/5/7 | 2/2/3 | — |
| chrona-roadmap/roadmap-marquee | 4/7/5 | 2/3/2 | — |
| chrona-roadmap/roadmap-sunday | 2/7/7 | 1/3/3 | — |
| controller-z/executive | 4/3/0 | 2/1/0 | — |
| controller-z/annotations | 4/3/0 | 2/1/0 | — |
| controller-z/plan-only | 0/0/0 | 0/0/0 | — |
| controller-z/elevated | 4/3/0 | 2/1/0 | — |
| controller-z/icons | 2/2/0 | 1/1/0 | — |
| controller-z/material-icons | 2/2/0 | 1/1/0 | — |
| controller-z/progress-track | 4/3/0 | 2/1/0 | — |
| controller-z/capabilities | 4/3/0 | 2/1/0 | — |
| controller-z/axis-alternating | 4/3/0 | 2/1/0 | — |
| controller-z/axis-interval-scales | 4/3/0 | 2/1/0 | — |
| controller-z/axis-cell-corners | 4/3/0 | 2/1/0 | — |
| controller-z/surface-glow | 4/3/0 | 2/1/0 | — |
| controller-z/region-frames | 4/5/2 | 2/2/1 | — |
| controller-z/annotation-kinds | 4/3/0 | 2/1/0 | — |
| controller-z/viewer-fit | 4/3/0 | 2/1/0 | — |
| controller-z/annotation-rounded | 4/3/0 | 2/1/0 | — |
| controller-z/group-header-runs | 4/3/0 | 2/1/0 | — |
| controller-z/group-child-indent | 4/3/0 | 2/1/0 | — |
| controller-z/slot-heading | 4/3/0 | 2/1/0 | — |
| controller-z/baseline-ghosts | 4/3/0 | 2/1/0 | — |
| controller-z/as-of-foot | 4/3/0 | 2/1/0 | — |
| controller-z/in-progress | 4/3/0 | 2/1/0 | — |
| controller-z/text-roles | 4/3/0 | 2/1/0 | — |
| controller-z-ja/executive | 4/3/0 | 2/1/0 | — |
| controller-z-ja/axis-secondary | 4/3/0 | 2/1/0 | — |
| halcyon-1/mission-brief | 0/0/0 | 0/0/0 | — |
| halcyon-1/programme-board | 4/7/12 | 2/3/6 | — |
| halcyon-1/launch-campaign | 0/0/0 | 0/0/0 | — |
| halcyon-1/tvac-slip | 0/0/0 | 0/0/0 | — |
| halcyon-1/dependency-network | 0/0/0 | 0/0/0 | — |
| halcyon-1/flight-readiness | 0/0/0 | 0/0/0 | — |
| halcyon-1/replan-baseline | 0/0/0 | 0/0/0 | — |
| halcyon-1/overlay-briefing | 0/0/0 | 0/0/0 | — |
| halcyon-1/glyph-gates | 8/5/16 | 3/2/7 | — |
| halcyon-1/gallery-editorial | 4/3/13 | 2/1/8 | — |
| halcyon-1/gallery-image-notes | 4/7/12 | 2/3/6 | — |
| halcyon-1/gallery-editorial-lanes | 4/3/13 | 2/1/8 | — |
| halcyon-1/gallery-text-compression | 4/7/12 | 2/3/6 | — |
| halcyon-1/target-b | 4/5/9 | 2/2/4 | — |
| halcyon-1/yuya | 4/5/14 | 2/2/4 | contrast×1 |
| halcyon-1/titlecard | 4/5/7 | 2/2/3 | — |
| halcyon-1/marquee | 4/5/7 | 2/2/3 | — |
| halcyon-1/sunday | 2/5/9 | 1/2/4 | — |
| halcyon-1/gates | 4/5/25 | 2/2/22 | — |

Contrast means `W_SCENE_MARK_CONTRAST`. The only newly reported diagnostics
are one progress-swatch contrast warning each in chrona-roadmap/roadmap-yuya
and halcyon-1/yuya; glyph-gates has no new contrast diagnostic. The Sunday
slides retain their expected keys without overflow (Halcyon7, roadmap6). Gates retains five
keys without a viewport warning. Outside legend primitives, all 25 changes
are text placements only: three note texts in each editorial slide move 17px
down, and 19 gates content texts move 18px up. Their text strings are
unchanged. No nonlegend mark geometry or actual dependency route changed.

## PNG and architecture evidence

Native CLI PNGs from [trial5 inputs9fa6062de](https://github.com/tya5/chrona/tree/9fa6062de/trial-5):

```sh
chrona render trial-5/plan/current.yaml --actual trial-5/plan/actual.yaml --preset executive-light --output actual.png --emit-scene actual.scene.json
chrona render trial-5/plan/current.yaml --preset trial-5/looks/target-b/preset.yaml --output no-comparison.png --emit-scene no-comparison.scene.json
```

Inspected Actual PNG SHA-256:
`b39b30e17ee9268ab1bb3bb3db2032f90be6961877a0f342140304f6f024582a`;
no-comparison PNG:
`f82b947d22c793752f33e03aa3b647c3fddc982084da181fd30882703a45c498`.
Supplemental Sunday, Gates and glyph-gates PNG rasterizations use SVGs verified
byte-identical to the official snapshot; PNG hashes are recorded in criterion 4.
Sunday has seven keys with no overflow; Gates has five keys with no viewport
warning. The two new Yuya progress-key contrast warnings remain visible and
unexempted.

Shared model paint remains project-independent; Layout owns potential/final
key selection and completed geometry; Scene consumes ink witnesses and owns
bounds-dependent effects; adapters infer no meaning. Independent review found
no layer breach. Exact-head CI and the exact-main release gate are still
pending.
