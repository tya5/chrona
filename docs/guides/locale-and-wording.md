# Localizing a render: `--locale` and wording

`chrona render --locale ja-JP` draws a picture for a Japanese reader. This guide says what the flag
changes by itself, what it leaves in English today, how to put the built-in texts under a locale, and how
to override any of them from a View. Every file below is written by the documented-command check and
every command runs, so the page cannot drift from the tool. The rules are Spec 06 section 9.3 (wording
precedence), Spec 24 (table headers), Spec 45 (legend vocabulary) and Spec 63 (the wording tables).

**Prerequisite: a CJK font.** Japanese text uses fonts installed in the environment; the product bundles none
(font policy, #1281). Before the Japanese example below, install a CJK font (on Ubuntu, `sudo apt-get install -y
fonts-noto-cjk`; macOS and Windows ship one) or the optional provider with
`pip install -e packages/chrona-fonts-noto-cjk` from a clone (the provider is not published; a wheel user follows
the OS-installed route). Without one, rendering Japanese fails with `E_FONT_GLYPH_UNAVAILABLE`. The repository's
wheel check exercises the clone route: it installs `packages/chrona-fonts-noto-cjk` into its clean environment
before running the Japanese block.

<!-- chrona:doc-check prerequisite: cjk-font -->

## 1. What `--locale` changes by itself

`--locale en-US` is the default; `ja-JP` is the other supported value. The locale selects the language of
**dates and axis names**: `Dec 2026` becomes `2026年12月`, `14 Dec 2026` becomes `2026年12月14日`. It also
selects the **wording table**, a bundled, closed list of built-in texts, one complete entry per locale.

A table entry is used only where a file asks for it with a **wording reference**, `{wording: <key>}`. A
text written as a plain string in a preset, View or Detail Profile is authored text and is never translated.
The bundled presets reference the keys for the words they share with the table: with the
default preset `--locale ja-JP` reads `タスク`, `計画`, `本日`, `計画期間`, `実績`, `マイルストーン` and `依存関係`, and the bundled
legends read `予定`, `基準計画`, `現行計画`, `ゲート`, `祝日` and `休業日` (the closed-day key reads `Non-working day`, no longer
`Weekend`). A bundled design's own voice (a title such as `THE KEY`, a marker such as `現在 NOW`, a subtitle) is authored text and is not translated.
To localize any other label, reference a key or override it in your own copy of the preset (sections 3 and 4).

The keys, with their `en-US` and `ja-JP` text:

| Key | en-US | ja-JP |
| --- | --- | --- |
| `column.task`, `column.plan` | Task, Plan | タスク, 計画 |
| `marker.today`, `marker.asOf` | TODAY, As of | 本日, 基準日 |
| `marker.baselineNew`, `marker.baselineRemoved` | new, removed | 新規, 削除 |
| `legend.planned` | Task duration | 計画期間 |
| `legend.actual`, `legend.milestone`, `legend.dependency` | Actual, Milestone, Dependency | 実績, マイルストーン, 依存関係 |
| `legend.asOf` | Today | 本日 |
| `legend.calendar-closed` | Non-working day | 休業日 |
| `legend.critical-edge` | Critical dependency | クリティカルな依存関係 |
| `legend.forecast`, `legend.progressFill`, `legend.snapshot`, `legend.deadlineMark` | Forecast (* estimated), Progress, Baseline, Deadline | 予測（*は推定）, 進捗, 基準計画, 期限 |
| `missing.unknown`, `missing.inProgress` | unknown, in progress | 不明, 進行中 |
| `column.lane`, `column.items` | Lane, Items | レーン, 件数 |
| `column.owner`, `column.number`, `column.phase`, `column.finishDelta` | Owner, No., Phase, Δ finish | 担当, 番号, フェーズ, Δ完了 |
| `column.finishDeltaPlan` | Δ vs plan | 計画との差 |
| `column.finishDeltaBaseline` | Δ vs baseline | 基準との差 |
| `legend.actual-ahead`, `legend.actual-on-track`, `legend.actual-behind` | Ahead, On track, Behind | 前倒し, 予定どおり, 遅れ |
| `legend.planned-plain`, `legend.baseline`, `legend.current-plan` | Planned, Baseline, Current plan | 予定, 基準計画, 現行計画 |
| `legend.gate`, `legend.holiday` | Gate, Holiday | ゲート, 祝日 |
| `summary.days` | DAYS | 日 |
| `legend.plan`, `legend.period`, `legend.depends-on` | Plan, Period, Depends on | 計画, 期間, 依存先 |
| `legend.missing-actual`, `legend.missing-actual-in-progress` | Not yet observed, In progress, not yet observed | 未観測, 進行中・未観測 |
| `legend.in-the-wings`, `legend.calendar-exception` | In the wings, Calendar exception | 出番待ち, カレンダー例外 |
| `legend.other` | Other | その他 |
| `column.no` | No | 番号 |
| `delta.unit.calendarDay`, `delta.unit.workingDay` | d, d | 日, 営業日 |
| `slot.notes` | Notes | 注記 |

`legend.calendar-closed` reads `Non-working day`, not `Weekend`, because the role also draws public holidays.
`column.no` is `No` without a full stop and `column.number` is `No.`: a `wording.keys` override is not locale-scoped
(section 4), so a design that wants the shorter header in English and Japanese needs its own key. `legend.other` is the
folded entry that a colour scale draws when there are more values than colours; the code names it, so it follows the locale
and can be overridden with `wording.keys` or `wording.legend.other`.

**Case belongs to the design, not to the key.** Every table value is neutral sentence case (`Today`, `Non-working day`).
A design that draws `as of`, `actual` or `non-working day` in lower case, or `TODAY` in capitals, sets the existing
typography `textTransform` token (`lowercase`, `uppercase`) on the role that draws the text (`legend` for the legend, `as-of-label`
for the as-of marker) and references the same key; it does not need a key of its own. The legend draws
`TASK DURATION` this way. A transform belongs to a role, so it applies to every entry of that legend and, for the as-of marker, to the
date after the label too (`as of 20 feb`). Japanese has no case and is unchanged by a transform.

**A slot heading.** A Layout Profile slot `heading.text` is a literal or `{wording: <key>}`, for example
`heading: {text: {wording: slot.notes}}` (`Notes` / `注記`). A literal stays as written under every locale, so a copied
layout that keeps `text: Notes` still draws English under `--locale ja-JP`; reference `slot.notes` to follow the locale.
The View's `wording.keys` override reaches it like any key, and a View `slotHeadingText` copy for the slot still wins. The
heading's role `textTransform` styles the resolved text as before.

**A Summary metric label.** A Summary Profile metric `label` is a string or `{wording: <key>}`, for example
`label: {wording: summary.days}` (`DAYS` / `日`); the View `wording.summary` entry still wins over it.

**The day unit of a delta.** A signed finish delta reads `+3d` in English and `+3日` in Japanese. The View's
`comparison.deltaUnit` picks the key: `calendar-days` reads `delta.unit.calendarDay`, `working-days` reads
`delta.unit.workingDay` (`d` in English for both, `営業日` in Japanese: `+3営業日`). A design that wants another unit text
sets `wording.keys: {delta.unit.workingDay: 営}` instead of a literal in its layout; the override reaches the table cell, the label on the bar and the Summary metric.

**Still English.** A text a preset author wrote as a plain string stays as written (titles, a design's marker text, panel
titles). Reference a key or override it in your own copy of the preset (sections 3 and 4). The Titlecard's secondary axis
names its month table (`nameTable: en-US`) on purpose, so it stays English next to the Japanese months. This page describes the tool as it is now.

## 2. A small plan that crosses a year

<!-- chrona:doc-check file: locale-plan.yaml -->
```yaml
version: timeline/v0.7
project:
  id: year-end
  title: Year-end release
  calendar: office
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  design:
    type: task
    title: Design
    schedule: {mode: fixed-span, start: 2026-12-14, end: 2026-12-25}
  build:
    type: task
    title: Build
    schedule: {mode: scheduled, amount: 15wd}
  launch:
    type: milestone
    title: Launch
    schedule: {mode: fixed-point, at: 2027-01-15}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-launch, type: dependency, from: {object: build, endpoint: end}, to: {object: launch, endpoint: at}, lag: 0d}
```

<!-- chrona:doc-check file: locale-actual.yaml -->
```yaml
version: chrona/actual-set/v0.3
kind: actual-set
id: year-end-observed
body:
  asOf: '2026-12-28'
  observations:
    - {id: design-1, sequence: 1, projectObjectId: design, actual: {start: '2026-12-14', finish: '2026-12-25', progress: 1}}
    - {id: build-1, sequence: 1, projectObjectId: build, actual: {start: '2026-12-25', openUntil: asOf, progress: 0.2}}
```

## 3. Reference the keys from a View and a Detail Profile

A View table column takes an optional `header`: a string or `{wording: <key>}` (without it the header is
the column `id`; the `id` is what rows and `hierarchyColumn` refer to, so it need not change). A View
marker `label` takes the same two forms. The View below is the default draft View with those three
references and a `wording.keys` override (section 4):

<!-- chrona:doc-check file: locale-view.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: ja-wording-view
body:
  heading: {text: {wrap: allow}}
  surface: table-timeline
  selection:
    include:
      types:
      - span
      - point
  grouping:
    by: hierarchy
    depth: all
    rollup: header
  hierarchyColumn: Task
  ordering:
    by: plannedStart
    direction: ascending
    tieBreak: id
  window:
    mode: selected-planned
  comparison:
    baseline: primary
    actual: optional
    observationSelection: latest
    deltaUnit: working-days
    facets:
    - planned
  progressFill:
    source: actual
  visibility:
    labels:
      placement: plot
      content:
      - title
      side: end
      overflow: suppress
    fallback:
      labels:
      - end
      - start
      - suppress
    relations:
      mode: semantic
      overflow: suppress
    annotations: none
  axis:
    tiers:
    - unit: year
      every: 1
      role: band
      typographyRole: axisQuarter
    - unit: quarter
      every: 1
      role: grid-major
    - unit: auto
      every: 1
      role: labels
      typographyRole: axisQuarter
      label:
        forms:
          month: short-month-year
          half: half-year
          year: year
        align: center
        overflow: thin-with-record
        orientation: horizontal
    - unit: auto
      every: 1
      role: labels
      typographyRole: axisMonth
      label:
        forms:
          day: localized-date
          week: start-day-month
          quarter: quarter
        align: center
        overflow: thin-with-record
        orientation: horizontal
    - unit: month
      every: 1
      role: grid-minor
  backgroundDecoration:
    rows: rules
    groups: all
  tableColumns:
  - id: Task
    header: {wording: column.task}
    text: {wrap: allow}
    source: title
    missing: em-dash
    align: start
    width: {minmax: {min: content, max: {fr: 1}}}
    headerOrientation: horizontal
  - id: Plan
    header: {wording: column.plan}
    text: {wrap: allow}
    source:
      facet: planned
    format: dateRange
    endDisplay: inclusive
    missing: em-dash
    align: start
    width: content
    headerOrientation: horizontal
  rows:
    mode: automatic
  markers:
  - kind: asOf
    source: actual
    label: {wording: marker.today}
  shading:
    nonWorking: true
    exceptions: true
  wording:
    keys:
      column.plan: 予定
      legend.calendar-closed: 休日
```

A Detail Profile `legend[].label` takes the same two forms, and it is where the legend text lives, so
the legend is localized by `--detail`:

<!-- chrona:doc-check file: locale-detail.yaml -->
```yaml
version: chrona/review-detail-profile/v0.1
id: chrona-builtin-editorial-detail
body:
  legend:
    - {role: planned, label: {wording: legend.planned}}
    - {role: actual, label: {wording: legend.actual}}
    - {role: milestone, label: {wording: legend.milestone}}
    - {role: dependency, label: {wording: legend.dependency}}
    - {role: asOf, label: {wording: legend.asOf}}
    - {role: calendar-closed, label: {wording: legend.calendar-closed}}
```

```sh
chrona render locale-plan.yaml --view locale-view.yaml --detail locale-detail.yaml --actual locale-actual.yaml --locale ja-JP --output locale-ja.svg
chrona render locale-plan.yaml --view locale-view.yaml --detail locale-detail.yaml --actual locale-actual.yaml --output locale-en.svg
```

In the Japanese picture the headers read `タスク` and `予定`, the marker and the `legend.asOf` entry read
`本日`, and the legend reads `計画期間`, `実績`, `マイルストーン`, `依存関係` and the override
`休日`. The English picture is the same file set without the flag: `Task`, `TODAY`, `TASK DURATION` and so on.
The progress fill reads `進捗` in Japanese and `PROGRESS` in English.

**The legend can show more than you list.** A Detail `legend` is the list you want first, but the renderer appends a key
for each meaning it actually draws and you did not list: `snapshot` (Baseline) when a baseline is drawn, `deadlineMark`
(Deadline) when a deadline is drawn, `forecast` when an item has a forecast, and `progressFill` (Progress) when a progress
fill is drawn in an ink different from its mark (the progress fill above is why `進捗` appears without a legend entry). Colour-scale
keys follow. To leave a key out, set `unkeyedLegendRoles` beside `legend` in the Detail Profile, for example
`unkeyedLegendRoles: [snapshot, deadlineMark]`; it admits only those two roles, and naming a role in both `legend` and
`unkeyedLegendRoles` is `E_DETAIL_LEGEND_POLICY`. Progress and forecast keys have no opt-out: do not draw them (omit
`progressFill` from the View and the Layout Profile `viewDefaults`, or give the progress fill the colour of its mark, which makes
the key redundant and omits it). An explicit `legend` entry for one of these roles replaces the default and sets its label and
order (Spec 28, "Default comparison keys").

## 4. Override any key from a View

A View's `wording.keys` maps a built-in key to your text. The View above sets
`column.plan: 予定` (instead of the table's `計画`) and `legend.calendar-closed: 休日` (instead of `休業日`).
An override is the View's own text, so it applies in every locale: the English picture above also shows `予定`
and `休日`. Write one View per locale if the text must differ.

The text of one label is decided in this order, the last one that applies winning:

1. the table entry for the render locale (`en-US` when the locale has none);
2. a literal authored in the preset, View or Detail Profile (never translated);
3. the View `wording.keys` entry for that key;
4. the View `wording.legend.<role>` or `wording.summary.<panel>.<metric>` entry, the most specific,
   which wins over `wording.keys["legend.<role>"]` if both address one legend label.

A wording reference (`{wording: legend.planned}`) takes the table entry at level 1, and level 3 or 4 still
replaces it. A plain string takes level 2, and level 3 or 4 still replaces it too: `wording.keys` also
reaches a legend label authored as a string, as long as its role is `R` and the key is `legend.R`.

A key that is not in the table is rejected, and nothing is drawn. For `wording.keys: {column.nope: x}`:

```json
{"status": "rejected", "diagnostics": [{"code": "E_VIEW_WORDING_UNKNOWN", "sourceRef": "/body/wording/keys/column.nope", "message": "wording key 'column.nope' is not a built-in wording key"}]}
```

Read the key list in section 1 (or `src/chrona/resources/wording-tables-v0.1.yaml` in a clone) and fix the
spelling; do not work around it with a string.

## 5. How years show in multi-year table dates

The `Plan` column decides once for the whole table. While every date in its ranges falls inside one calendar
year, a range omits the year (`11月2日 – 11月6日`). As soon as any range in the table crosses a year boundary,
as in the picture above, every date in that column carries its year, including ranges that sit inside one year
(`2026年12月14日 – 2026年12月24日` beside `2026年12月25日 – 2027年1月14日`). A single date (the milestone)
always carries its year. English reads the same way: `25 Dec 2026 – 14 Jan 2027`.
The axis is separate: its upper tier names the month and year (`2026年12月`, `2027年1月`) and the lower tier
the day.
