# Issue 1679 — realized legend acceptance

<!-- chrona:literal-acceptance/v1 -->

Implementation `19c89498b`, glyph-dash correction `0fe79a9f6`, clipping test
`380cab8b3`. [Current design/plan](../../planning/active/issue-1679-realized-legend-work-record-2026-10-18.md).
Local evidence below is not release acceptance. [PR1692](https://github.com/tya5/chrona/pull/1692)
head `1ecf36452` fails snapshot generation in
[CI39088644589](https://github.com/tya5/chrona/actions/runs/39088644589): two
strict glyph legend contrast errors. Reproduction fails because the snapshot
was never uploaded; readiness fails on that dependency; tests were skipped.
Implementation is paused for the composite-key correction in the work record.
Keep the issue open; official artifact and exact-main release remain required.

## Literal issue acceptance

### Issue #1679

- Source: [Issue #1679](https://github.com/tya5/chrona/issues/1679)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A synthetic project with actuals, rendered with executive-light: every distinct realized mark paint has exactly one legend key, and the actual and progress keys use the realized paints. | not met | [Native/SVG tests](../../../tests/integration/test_realized_legends.py) cover scalar paints and Progress, but [CI39088644589](https://github.com/tya5/chrona/actions/runs/39088644589) exposes multipart glyph parts incorrectly split into isolated keys. Composite regression/correction required. | — |
| 2 | When an encoding replaces the planned paint on every planned mark, no base planned swatch remains; the encoding's entries stand in its place. A mixed case (some planned marks unencoded) keeps the base key. | met | [Native encoding tests](../../../tests/integration/test_realized_legends.py): all-covered View encoding removes Planned; selective Style encoding retains the unencoded base witness. Existing scoped-legend and finite-swatch tests retain their geometry/paint assertions. | — |
| 3 | target-b without snapshot or actual has no baseline, actual or in-progress keys and no empty Δ column. | met | [Pinned trial5](https://github.com/tya5/chrona/tree/9fa6062de/trial-5) target-b native PNG/Scene inspected: unavailable keys and Δ cells/header removed. Native synthetic absent/supplied-empty and Snapshot-only tests retain source-presence distinctions. | — |
| 4 | A count table of the public example changes, and the PNGs checked. | met | [Count table and PNG evidence](#public-count-table): all50 materializers completed into disposable outputs;42 SVG/Scene pairs change,8 remain identical. New warnings are disclosed, not repaired through corpus edits. | — |

## Programme-level criteria (optional)

## Public count table

Local snapshot: `0fe79a9f6`; baseline: committed materializer evidence on
implementation base `82c1e96b6`. The later allocation-preservation correction
restores final fit warnings; its official artifact must confirm or update this
table before release acceptance. Do not treat this preliminary table as the
final merged-main output.
Counts are added/removed/changed **by primitive ID**; text counts are a subset.
Every slide has **0/0/0 dependency-route changes** (legend line keys are not
routes). No source YAML or canonical generated output was edited.

| Slide | Primitives +/−/~ | Text +/−/~ | New diagnostics |
| --- | --- | --- | --- |
| aster-ssd/overview | 2/2/0 | 1/1/0 | — |
| chrona-roadmap/roadmap | 6/6/7 | 3/3/3 | — |
| chrona-roadmap/roadmap-yuya | 8/7/12 | 4/3/3 | contrast×1 |
| chrona-roadmap/roadmap-titlecard | 8/5/7 | 4/2/3 | — |
| chrona-roadmap/roadmap-marquee | 8/7/5 | 4/3/2 | — |
| chrona-roadmap/roadmap-sunday | 8/7/7 | 4/3/3 | legend overflow×1 |
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
| halcyon-1/glyph-gates | 10/5/16 | 5/2/7 | contrast errors×2 |
| halcyon-1/gallery-editorial | 4/3/13 | 2/1/8 | — |
| halcyon-1/gallery-image-notes | 4/7/12 | 2/3/6 | — |
| halcyon-1/gallery-editorial-lanes | 4/3/13 | 2/1/8 | — |
| halcyon-1/gallery-text-compression | 4/7/12 | 2/3/6 | — |
| halcyon-1/target-b | 8/5/9 | 4/2/4 | — |
| halcyon-1/yuya | 8/5/14 | 4/2/4 | contrast×1 |
| halcyon-1/titlecard | 8/5/7 | 4/2/3 | — |
| halcyon-1/marquee | 8/5/7 | 4/2/3 | — |
| halcyon-1/sunday | 8/5/11 | 4/2/5 | legend overflow×1 |
| halcyon-1/gates | 4/5/25 | 2/2/22 | canvas exceeds viewport×1 |

Contrast means `W_SCENE_MARK_CONTRAST`; legend overflow means
`W_LAYOUT_VISIBLE_OVERFLOW`; canvas means `W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT`.
Two glyph contrast errors block release and require the structural correction;
the five warnings require explicit reviewer disposition. Sunday's
fixed key frame no longer contains every correct entry; no core rule hides a
key or enlarges project-specific frames. New low-contrast swatches expose the
existing realized ink. No diagnostic gate was weakened.

Outside legend primitives, editorial/editorial-lanes move their three note
texts17px downward to reserve Progress. Gates shifts19 side-content texts as
the legend reservation grows. No mark/route geometry changes. The initial
batch detected lost snapshot-glyph dashes; the shared witness correction was
regression-tested and only the affected five roadmap slides rerendered. All
their nonlegend snapshot records now exactly match the baseline.

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
Supplemental before/after public SVG rasterizations use installed resvg and
repository Noto fonts: glyph-gates, editorial, gates, Yuya and Sunday inspected.
The new keys fit except the disclosed Sunday fixed-frame overflow; no new
mark/note collision or image crop was observed. These are local inspection
records, not claimed CI artifacts.

Shared model paint remains project-independent; Layout owns potential/final
key selection and completed geometry; Scene consumes ink witnesses and owns
bounds-dependent effects; adapters infer no meaning. Independent review found
no layer breach. Combined focused unit run179 passed; migrated legend-native
batch58 passed; final Actual/paint batch24 passed. Scene delivery:33 dataclasses,
249 fields explicitly owned; reachability:299 modules, no orphans.
