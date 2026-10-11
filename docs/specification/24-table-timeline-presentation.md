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

### 2.1 Table and row metrics (#480)

Layout measures a table once. The same measure sizes the `table` source and
places its columns. A column's natural width is its widest header or cell text,
measured in that text's own typography role, plus the cell inset. For the
hierarchy column, each cell's extent includes its row's indent. The table content
extent is the sum of natural widths and the gutters between columns. A table slot
at `inlineSize: content` receives the larger of this extent and
`column count × table.column.minInlineSize`. The metric is a per-column floor for
a content-sized slot, not a column minimum. Any surplus goes to flexible columns.

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

View `tableColumns[].text` and `heading.text` reuse `{wrap: allow|forbid}`;
absence means `forbid`. Column intent covers its header and cells. Heading
intent covers kicker/title/subtitle and the implicit Project title. Layout
uses the existing measured word/CJK wrapping mechanism and typography/run
metrics. Fitting text returns its exact source unchanged, without whitespace
normalization. An indivisible overlong unit uses source-preserving ellipsis
and `W_LAYOUT_TEXT_ELLIPSIZED` naming that text and its measured shortage;
no abbreviation dictionary or font-size reduction is implied.

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
