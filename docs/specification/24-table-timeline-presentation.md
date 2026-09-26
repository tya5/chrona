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

The application normalizes every cell into `SurfaceContentInput` before Scene
construction: `blank` becomes the empty string, `em-dash` becomes `—`, and `unknown`
becomes the literal `unknown`. Scene emits that normalized text verbatim. Neither
Scene nor SVG receives the enum as a display string or selects an alternative default.

For View v0.2 explicit Review rows, the table has one record per Review row rather than
per semantic Project object. The row label supplies its title cell and `tableSubject`
supplies object-derived cells. Timeline marks remain one per ordered Review Item and
share their row's bounds through Scene-assigned subtracks. This preserves a coherent
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
