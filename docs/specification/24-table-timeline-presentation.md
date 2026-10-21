# Table-Timeline Presentation Design

**Status:** Design complete; M27 product binding accepted  
**Owns:** the M15 table-timeline projection, profile, Scene, and SVG adapter boundary.

The historical axis formatter and Scene-ownership wording below is superseded
for the current runtime by [Axis Name Tables](63-axis-name-tables.md) and the
constraint-driven Layout architecture. It is not a second formatter contract.

## 1. Contract

M15 composes a semantic table and a Date timeline from one immutable View Projection.
The View selects row facts through `tableColumns`; the table-timeline profile selects
geometry and axis policy; Style/Theme resolves declared roles; Scene preserves source
identity; the adapter emits SVG. Project, Schedule, Actual, and federation inputs are
read-only and retain their existing authority.

The adapter MUST be generic over those resources. It MUST NOT branch on a preset ID,
Project title, image concept, or Controller Z identity. A light executive composition is
a user-editable preset/fixture, not a Python rendering mode.

`tableColumns` is ordered and closed. A column may expose `id`, `title`, `objectType`,
`entity`, one declared typed field, or one requested comparison facet. A field that is
not declared by the active profile, and a comparison facet absent from the View, are
diagnostics. Missing data uses the declared `blank`, `em-dash`, or `unknown` treatment;
no formatter code, title parsing, or renderer field lookup is permitted.

A column MAY declare `header` (#1724), a literal or a `{wording: <key>}` reference resolved from the bundled wording table for the Render Context locale ([Axis Name Tables](63-axis-name-tables.md#built-in-wording-tables), [View Model §9.3](06-view-model.md)). Absent, the header text is the column `id`; rows, `hierarchyColumn` and styles keep referring to `id`. The absent-value words `unknown` and `in progress` use the same table (`missing.unknown`, `missing.inProgress`). The default lane-table headers (`Task` or `Lane`, and `Items`) use `column.task`, `column.lane` and `column.items` for the locale; a declared lane `columns[]` entry may carry `header` (a literal or `{wording: <key>}`); absent, the header is its `id`.

A column MAY name `textRole` (#1062), a Theme text role in which its cells are measured and set. Absent, the cells keep `text` (`numeric` for a signed format). Layout measures, wraps and places the column in that role (size, weight, letter spacing, transform and line height, through the same channel as any cell role) and the row block follows the tallest role a row holds. Scene paints a plain cell with the role's `fill` when the Theme binds `<role>.fill` and with the `text` ink otherwise; a state-coloured cell (variance, missing actual) keeps its state ink and takes only the role's typography. The header keeps its own role. A role the Theme does not declare is `E_THEME_ROLE_REQUIRED` at `/body/tableColumns/<index>/textRole`. The ink is ground text for the contrast gate (blocking at 4.5 on its ground). Work record: [issue-1062-text-roles-2026-10-04.md](../planning/active/issue-1062-text-roles-2026-10-04.md).

The application normalizes every cell into `SurfaceContentInput` before Scene
construction: `blank` becomes the empty string, `em-dash` becomes `—`, and `unknown`
becomes the literal `unknown`. Scene emits that normalized text verbatim. Neither
Scene nor SVG receives the enum as a display string or selects an alternative default.

For View v0.2 explicit Review rows, the table has one record per Review row rather than
per semantic Project object. The row label supplies its title cell and `tableSubject`
supplies object-derived cells. Timeline marks remain one per ordered Review Item and
share their row's bounds through Layout-assigned subtracks. This preserves a coherent
table/timeline alignment without treating a milestone, Snapshot, or Actual as a special
renderer case.

### 1.1 Date-range endpoint display (#1293)

A `format: dateRange` column MAY declare `endDisplay: inclusive | exclusive`.
Omission means `exclusive` and preserves existing authored output. The property
is valid only for `dateRange`; invalid values or formatter combinations fail
View validation. The live View schema adds this optional property in place.

**Year in table dates (#1724).** A `dateRange` cell shows a date without its
year only while every date displayed in the table's `dateRange` cells (the
range ends actually rendered, after `endDisplay`) lies in one calendar year; the
padded axis window alone never adds a year. A range crossing a year inside one
cell shows both years as before. When the displayed dates span more than one
calendar year, every date in every `dateRange` cell carries its year
(`27 Apr 2027 – 03 May 2027`; `2027年4月27日 – 2027年5月3日` for `ja-JP`, the year
leading the month and day). A table whose displayed dates share one year renders
exactly as before, whatever the plan or window span.

For a complete half-open interval with date-valued `start < end`, exclusive
display formats the stored endpoint. Inclusive display of a planned span whose
schedule is a WorkPeriod in working days (`wd`) formats the last working day
before the exclusive end, using the object's calendar and then the Project
calendar. If neither declares a calendar, each calendar day counts as working;
no weekday calendar or warning is invented. Other planned spans, including
calendar-day (`d`) and week (`w`) schedules, and explicit Actual intervals use
the civil day immediately before the exclusive end. Planned `end` and Actual
`finish` retain their half-open endpoint meaning (Specs 03 §4 and 06 §4). This
display calculation does not mutate the source, schedule, deltas, or bar geometry.

An inclusive one-day interval collapses to one compact date without a year:
`[2027-01-04, 2027-01-05)` reads `04 Jan` in `en-US` and `1月4日` in `ja-JP`.
Other complete ranges retain the existing locale and same-year/cross-year
formatting, using the displayed endpoint. Points, missing values, incomplete
or open intervals, and non-positive ranges retain their existing formatting;
this option introduces no temporal data validator.

The View's `comparison.deltaUnit` selects calendar-day or effective-calendar
working-day distances for projected start, finish, and point comparisons. A
working-day finish variance uses the item's effective calendar; when absent, it
counts all calendar days. This delta policy does not change the display rule for
`endDisplay: inclusive` above.

Bundled draft and named preset defaults select `working-days` for this shared
comparison fact, including in-plot labels. An explicitly authored View may
still select `calendar-days`; adapters never override the declared unit.

Content normalization applies this rule once, before affixes and Layout
measurement. Layout receives completed cell text; Scene and adapters emit it
without endpoint calculation. The bundled default and every builtin preset
declare inclusive display on their date-range columns through the packaged
resource authority (Spec 32 §4). Existing example Views are not rewritten;
changed corpus cells and their causes must be listed with the migration.

### 1.2 In-progress Actual observations (#1582)

A selected interval Actual with `start` and no `finish` is in progress, independent
of its `progress` value. The renderer-neutral Review semantics retain that source
meaning; Layout draws the Actual mark from its observed start to the Actual Set's
`asOf`. It does not synthesize an `actual.finish`. Where the View selects the
existing Actual `progressFill`, the Theme's existing fill policy draws the declared
fraction inside this Actual mark. A missing start remains an incomplete Actual and
emits `W_LAYOUT_ACTUAL_INCOMPLETE`; a started Actual without an `asOf` uses the
existing open-Actual as-of-required diagnostic/absence, and a zero-length cutoff
retains its existing invalid-cutoff diagnostic/absence behavior.

The open Actual's outline is the single Layout-completed duration path, not a
milestone glyph fitted across the time interval. `milestoneSymbolActual` remains a
point-only geometry choice. This keeps the progress-fill clip host identical to the
completed open-span mark while leaving the Actual paint role unchanged. A multipart
point glyph's Layout-completed progress contour retains its logical mark owner
separately from any Scene clip host; this does not alias a glyph part as the mark.

For a started open Actual, `finishDelta` is absent until `asOf` is past the planned
exclusive end. Once past it, the canonical variance is `asOf` minus that end, so
table and label consumers report the delay known at the cutoff. Missing-value text
for an in-progress delta remains controlled by the View column's `missingBy`
member; the packaged target-b, marquee, sunday, titlecard and yuya designs use
`blank` for that state. A known variance takes precedence over that missing-state
text. The `missingActualScope` policy cannot relabel a recorded Actual as missing.

## 2. Axis, groups, and layout

The View continues to own its explicit temporal window. The profile may use two or
three Date levels from `quarter`, `month`, and `week`; tick generation is derived solely
from that window and explicit Render Context locale. Major/minor grid roles are Scene
primitives, not visual defaults. There is no local-clock “today” marker; an as-of marker
requires an explicit Render Context date.

View grouping supplies stable keys and order. Profile modes have exact semantics:
`none` emits no group surface or separator; `separator` emits only a boundary;
`band` emits only a group background; `header-and-separator` emits a labelled header and
boundary. `gapRows` is applied only between groups. The M14 profile must conform to this
definition before M15 code reuses it.

The profile owns column sizing, row metrics, clipping, and exclusion zones. Relations
and annotations route deterministically around the table, headers, group surfaces, and
bars. A collision that cannot be routed produces a diagnostic and a text alternative;
routes never become View coordinates.

### Hierarchy expressions and column width (#437)

These mechanisms express different facts; a shared tree shape does not make
them interchangeable:

| Mechanism | Authority and meaning |
| --- | --- |
| Automatic rows with `grouping.by: hierarchy` | View projects Project parent/child containment; depth and rollup follow that projection. |
| Explicit rows with `depth` and optional `parentRow` | View-local presentation nesting, not an assertion or override of Project containment. |
| Columns with `source: wbsCode` or `source: path` | Display content: an authored Project WBS code or its resolved hierarchy path, not another row-nesting declaration. |

Project containment remains Core-owned. WBS strings are not parsed for parents
or checked against indentation. WBS/path columns compose with either row mode.
Automatic rows do not contain authored `items`; explicit rows prohibit automatic
`selection`, `grouping` and `ordering` (`E_RESOURCE_SCHEMA`). Thus automatic
hierarchy projection and an explicit row tree cannot compete in one View.
[Specification38](38-review-row-composition.md#1-contract) owns row composition
and local parent-graph validation; [Specification06](06-view-model.md) owns View
selection intent. Layout completes indentation; Scene/adapters preserve it.

Visible nesting requires `hierarchyColumn`, naming exactly one `tableColumns`
ID, irrespective of its position. Missing, unknown and unused declarations are
`E_VIEW_HIERARCHY_COLUMN_REQUIRED`, `E_VIEW_HIERARCHY_COLUMN_UNKNOWN` and
`E_VIEW_HIERARCHY_COLUMN_UNEXPECTED`; duplicate column IDs are
`E_VIEW_TABLE_COLUMN_DUPLICATE`. Non-hierarchy header groups may also declare
the column under the parent-header rule below; a band alone is not nesting.

The column `width` grammar introduced in View v0.17 and retained by current
View v0.28 is the **table subset**, not the complete Layout size grammar:

```text
content | fill | {fr: weight}
        | {minmax: {min: content, max: content | fill | {fr: weight}}}
0 < weight <= 1000000
```

Each object is closed; `fr` is a number, and `minmax` requires both members.
`min-content`, `max-content`, `fixed`, `fitContent` and `aspectRatio` are not
column widths and fail schema validation. Fixed physical geometry belongs to
the Layout Profile: fix or bound the `table` track using
[Specification33 §5](33-intent-oriented-layout.md#5-size-and-distance-values). This stabilizes
the table host, not an independently fixed individual column. Column allocation
uses measured content and gutters; at most one `fill` maximum is allowed,
otherwise Layout reports `E_LAYOUT_TABLE_OVERFLOW`. The shared schema authority
is `common-v0.1.$defs.tableColumnPresentation.properties.width`.

**Empty table slot (#1683).** Only `rows.mode: lanes` draws its own columns (from `rows.laneTable`); every other row mode
takes its columns from the View's `tableColumns`. A View with no column source has nothing for the `table` slot to hold,
so that slot is measured empty and collapses to zero width: an `fr` share of the free space is never reserved for a blank
table, and the plot takes the room. Declare `tableColumns` to show a table.

**Declared comparison columns and `priority` (#1869).** A comparison column (`facet` or `comparisonFacet` of
`finishDelta`, `startDelta`, `atDelta`, `progress`, `missingActual`, `actual`, or a `scenario` source) is omitted
when its data source is unbound (no Actual Set, no bound scenario), so the table and the time scale change width
when the data arrives. A column MAY declare `priority`: `optional` (the default, and the value when absent) keeps
that omission; `preferred` or `required` keeps the column, with its header and blank cells, at the width its
`width` declares, so the scale is the same before and after the data. The member is additive and
behaviour-preserving when absent (Spec 56 §3.2). It does not affect an unbound field-role column, which is always
omitted (Spec 06), nor a column whose source is bound.

### 2.1 Table and row metrics (#480)

Layout measures a table once. The same measure sizes the `table` source and
places its columns. A column's natural width is its widest header or cell text,
measured in that text's own typography role, plus the cell inset. For the
hierarchy column, each cell's extent includes its row's indent. The table content
extent is the sum of natural widths and the gutters between columns. A table slot
at `inlineSize: content` receives the larger of this extent and
`column count × table.column.minInlineSize`. The metric is a per-column floor for
a content-sized slot, not a column minimum. Any surplus goes to flexible columns.
Natural demand and full-text fit admission share one Layout-owned composition of
measured text advance, hierarchy indent and inset (#1841). A complete header or
cell fits when that demand fits its allocated column; reverse floating-point
subtraction of the same chrome must not invent a shortage. Apply this also to
bounded/wrapped and affixed content; genuine shortage retains the declared
overflow policy. Do not add a tolerance or inflate column widths to hide it.

**Rows under group headers (#1065).** The View's `hierarchyColumn` names the table column that carries row
nesting. Hierarchy grouping, a row `depth` and a `parentRow` nest rows with their own depths: a grouped row starts
the group's inset plus `table.indent.inlineSize` times its depth after the column start. When the View groups by
a non-hierarchy dimension (a field or the object type) with `presentation: header` and declares no other
nesting, a group header is a parent row in reading order and every grouped row is one step below it: the row's
label in the hierarchy column starts exactly `table.indent.inlineSize` after the header's label start. In the
first column that is the table start, after a start-position group tab and its gap (#882) when the Theme draws one;
in a later column the step is counted from that column's start. The header label, the bands, the tab and the tint
do not move. Natural column width includes this indent as for any hierarchy cell, so a content-sized table is
never narrower than its widest indented label; a flexible column cuts the label with its source kept, as for any
cell. A Theme whose `groupHeader` role is vertical draws no header row (#585), so nothing is indented. Without
header groups (field grouping with `presentation: band` or none) a declared `hierarchyColumn` is
`E_VIEW_HIERARCHY_COLUMN_UNEXPECTED`, as before. The previously rejected combination becomes valid; accepted
documents render byte for byte as before.

A table slot at `inlineSize: {minmax: {min: content, …}}` uses this same measured
content extent as its minimum (#487): the slot is never narrower than its measured
columns and gutters, regardless of a flexible track's allocated share. See
Specification 33 §5 for how a flexible track resolves a `minmax` minimum against its
share.

**Bounded table text (#1295).** An optional table slot `maxInlineShare`
(Specification 33 section 6) takes precedence over unbroken natural content
floors, not over authored fixed dimensions. Layout measures the required cell
insets, hierarchy indents, group tabs, icon/affix reservations, gutters and permitted ellipsis at the bounded
column widths; an infeasible mandatory minimum is `E_LAYOUT_TABLE_OVERFLOW`,
never uniform font/column shrink or a wider table/timeline host.

If natural columns fit, preserve the ordinary column allocation exactly. On
shortage, reserve every column's measured mandatory minimum and the gutters.
Non-flexible `content` columns share the budget remaining after flexible minima,
with equal weights and their natural widths as upper bounds. Allocate the rest
to `fr`/`fill` columns using their declared weights and mandatory floors, by the
same bounded flexible-track rule as Specification 33 section 5. If the mandatory
minima and gutters alone exceed the slot, fail with `E_LAYOUT_TABLE_OVERFLOW`;
do not proportionally shrink completed columns or their typography.

View `tableColumns[].text`, `rows.laneTable.text` and `heading.text` reuse `{wrap: allow|forbid}`;
absence means `forbid`. These optional intents use the live View v0.28 contract. A packaged reference
View still on v0.27 migrates to the existing v0.28 version before adopting them;
independently authored corpus Views are not rewritten by this migration.
Column intent covers its header and cells. Heading intent covers
kicker/title/subtitle and the implicit Project title. Layout
applies lane-table intent to both derived columns (lane label and optional
item count), without changing lane membership or source facts. Table wrapping
also works in an authored fixed/flexible track without `maxInlineShare`;
the implicit full-share budget closes at the actual allocation, not the
unbroken natural width. An explicit table share takes precedence.
Layout
uses the existing measured word/CJK wrapping mechanism and typography/run
metrics. Fitting text returns its exact source unchanged, without whitespace
normalization. An indivisible overlong unit uses source-preserving ellipsis
and `W_LAYOUT_TEXT_ELLIPSIZED` naming that text and its measured shortage;
no abbreviation dictionary or font-size reduction is implied.

For heading text with `wrap: allow`, each run's inline advance is reserved
before fitting. Close every part's lines and the whole heading's baseline stack
at the independently allocated track width before block allocation. If even the
measured ellipsis and that reservation cannot fit, fail with
`E_LAYOUT_TEXT_OVERFLOW`; do not report table infeasibility or enlarge the track.

When a bounded cell with declared affixes requires ellipsis, retain its prefix
and suffix verbatim around the longest measured source-core prefix plus `…`.
If even the complete affixes and ellipsis cannot fit, the mandatory minimum
is infeasible. Rotated headers reserve their native inline thickness and their
text advance as block demand, not the column width as horizontal text space.

Bounded column measurement precedes header and row/lane allocation. The header
prefix reserves its completed multiline requirement; each row includes its
own tallest completed multiline cell, in the cell's typography role. Heading
line demand similarly precedes track allocation; wrapping is not a post-Scene
newline or clip. Scene/adapters preserve completed lines and geometry. Without
the optional declarations, existing natural-width and overflow behavior is
unchanged. Packaged default/builtin declarations migrate atomically; fitting
short-title geometry, paint, routes and diagnostics remain unchanged, with only
enumerated resource-identity provenance changes for the migrated resources.

A review row's block requirement is the largest of: `timeline.row.minBlockSize`;
its mark-track extent plus `timeline.row.paddingBlock`; and the largest line block
(`fontSize × lineHeight`) among its table cell roles plus
`timeline.row.paddingBlock`. `paddingBlock` is the row's total block padding,
added once. The pre-layout content requirement and row placement use this one
rule. A table cell's line box is centred in its row using the cell's own role.
Plot labels are not row-held text under this rule.

The packaged default's `timeline.row.minBlockSize` is a Theme number-token
expression, `{timeline-mark-size} + {timeline-row-padding}`, not an independent
fixed pitch. Existing ingress number-expression resolution closes that floor;
Layout then applies the completed mark/text maximum above, including measured
wrapped cell lines. With the default34px mark and8px total padding,14px text at
line-height1.4 gives42px rows;40px text gives64px rows. These are consequences
of declarations, not preset-specific branches or caps. Custom bound row floors
remain authoritative; mark size stays bound, avoiding circular derivation.

A declared comparison stack (#1149) reserves its completed outer block extent,
including span-frame padding, for row requirements and inter-track pitch. An
oversized stack grows that reservation without resizing its nominal track;
ordinary, folded-header and lane placements use the same Layout allocation.

Derived sizes (#1150). A Theme that leaves `timeline.mark.blockSize` unbound gets the track
`timeline.row.minBlockSize` less twice `timeline.row.paddingBlock` (a padding above and below the
track), so changing the row moves the track with no other edit; a bound value is used as declared, and a row that leaves no positive
remainder is `E_LAYOUT_METRIC_REQUIRED`. Every bundled Theme binds it, so nothing they render changes.

A Theme that leaves `timeline.axis.blockSize` unbound gets the sum of the axis lanes: each horizontal
`labels` tier's declared `laneBlockSize` (else its label block, the same lane rule the axis uses to place
the tier), stacked; several `band` tiers without a label lane of their own stack theirs, and the axis
holds the taller of the two stacks. A View whose labels tiers include a rotated one has lanes that depend
on the interval widths, so its axis stays required (`E_LAYOUT_METRIC_REQUIRED`). A Theme that leaves
`table.header.blockSize` unbound gets the axis block size, bound or derived, so the table header ends where
the axis ends. A bound value is used as declared.

Axis intervals are natural calendar intervals from the resolved View window. The
declared axis formatting and explicit Render Context locale determine each label. Scene
measures labels before emission; if a required label does not fit its resolved axis
slot, it diagnoses overflow instead of using a fixed day stride, overlapping labels,
or an out-of-bounds final label.

## 3. Scene and output

New primitives are `tableHeader`, `tableCell`, `axisBand`, `gridLine`, `groupSurface`,
and `routedConnector`. Each carries `sceneId`, `sourceRef` (or explicit derived metric
source), purpose, role metadata, and text equivalent. SVG requires the existing source
metadata/accessibility capabilities plus `tableSemantics` and `hierarchicalAxis`.

## 4. Non-goals

M15 does not add status semantics, forecasting, date-time axis behavior, arbitrary cell
formatters, drag coordinates, PDF/raster output, or automatic relation changes.
