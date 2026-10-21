# View Model

**Status:** Draft
**Depends on:** `01-concepts.md`, `02-domain-model.md`, `03-temporal-model.md`, `04-scheduling-model.md`, `05-project-format.md`  
**Owns:** selection, comparison context, grouping, ordering, temporal-window selection, visibility, layout intent, and presentation annotations.

## 1. Purpose

A View is a reproducible presentation projection over a semantic Project. It answers **which** information is shown and **where it is arranged**. A View does not change the meaning of a Project object, date, dependency, schedule, Snapshot, or Actual observation.

```text
Project  = What exists and what it means
View     = Which information is shown and where it is arranged
Style    = How selected information is expressed visually
Theme    = Concrete visual tokens
Scene    = Renderer-neutral visual primitives
```

### 1.1 Design drivers from prior research

Chrona is not a generic project-management suite, a Mermaid-only diagram DSL, a slideware clone, or a pixel-authoritative canvas. Existing tools expose complementary but insufficient trade-offs:

- project-management and Gantt tools commonly add workflow, resources, cost, and portfolio machinery that is outside Chrona's purpose;
- Git-friendly diagram DSLs preserve reviewability but do not provide enough timeline annotation and presentation freedom;
- canvas editors such as tldraw are valuable future interaction surfaces, but their scene state would create noisy diffs if it became the Project source of truth; and
- slide tools provide expressive callouts and emphasis but hide schedule semantics inside geometry.

The View Model therefore preserves semantic, Git-reviewable Project data while allowing multiple review-focused projections, named comparisons, and anchored presentation annotations. Its purpose is to make semantic changes visible without turning presentation state into the model.

## 2. Invariants

- A View MUST NOT mutate Project data, scheduling results, Snapshot data, or Actual observations.
- A View MUST NOT make Actual observations scheduling inputs or infer a rescheduling policy from them.
- A View MUST identify Project objects by stable project-local IDs, never by title, visual position, or renderer identity.
- A View MAY select a resolved federated summary object only by its stable derived
  `federation-id:child-object-id`, never by a child title or a live repository lookup.
- A View MUST be reproducible from explicit input references and View parameters.
- A View MUST NOT own colors, fonts, stroke widths, renderer-specific state, or absolute scene coordinates.
- Omitting an item from a View MUST NOT delete or alter the underlying semantic item.

## 3. View Context

A View is evaluated against an explicit View Context.

| Input | Meaning | Required |
|---|---|---|
| Primary Project | Semantic project data and its derived planned schedule | Yes |
| Snapshot | Named immutable comparison state, potentially identified by a Git ref | No |
| Actual observations | Observed start, finish, point occurrence, and progress | No |
| Federation Plan | Pinned, read-only subproject summary inputs declared in a separately versioned parent-side plan | No |
| Render context | Explicit evaluation date, locale, and other environment data | As required by the consumer |

The primary Project is required. Snapshot and Actual inputs MUST be named when present. A View or renderer MUST NOT silently select “latest”, “main”, or a local-clock date as a comparison source.

A federated item is a read-only projection input after the Federation Plan's pinned
reference has been resolved. It may be selected, grouped by federation ID, and styled
by declared origin. It cannot be edited through the parent's View and it must not cause
the parent scheduler to inspect non-published child internals.

Serialization for Views, Snapshots, and Actual observations is outside this document. The View Model defines their presentation semantics only.

## 4. View Definition

A View definition is declarative. Its common resource envelope, reference syntax, and
normalization belong to [Presentation Format](13-presentation-format.md); this document
owns the View-body meaning and v0.1 field language below.

| Concern | View responsibility |
|---|---|
| Selection | Include or exclude objects, relations, entities, and annotations |
| Grouping | Partition selected objects into lanes from semantic fields |
| Ordering | Deterministically order groups and objects |
| Temporal window | Select the presented time interval |
| Comparison | Declare which named comparison inputs and facets the View accepts or requires; the concrete Project, Snapshot, and Actual references come from the Render Context |
| Visibility | Select labels, relations, annotations, and comparison facets |

Selection expressions MUST be declarative predicates over semantic data and MUST NOT execute arbitrary host-language code.

### 4.1 v0.1 persistent body

The v0.1 View resource uses a deliberately small, closed selector language. It enables
reviewable plan-versus-actual views without embedding code or renderer geometry:

```yaml
# chrona-contract: historical
version: chrona/view/v0.1
kind: view
id: controller-review
body:
  selection:
    include: { types: [span, milestone] }
  grouping: { by: entity, missing: ungrouped }
  ordering: { by: plannedStart, direction: ascending, tieBreak: id }
  window: { mode: selected-planned, marginDays: 7 }
  comparison:
    actual: required
    facets: [planned, actual, startDelta, finishDelta, progress, missingActual, unmatchedActual]
  visibility: { labels: true, relations: semantic, annotations: all }
```

`selection.include` is an intersection of its declared filters. v0.1 permits only
stable IDs, object types, entity IDs, profiles, and declared typed-field equality; an
omitted filter does not constrain selection. There is no arbitrary boolean expression,
regular expression, title match, script, or implicit hierarchy traversal. The exact
typed-field reference form is introduced only with the Extension schema.

**Completion selection (#1812).** `selection.exclude.state: [finished]` is an
optional closed vocabulary predicate on the current Primary selection. Its
selected Actual facts use Core's completion rule (Spec04 §17.1): a span needs
observed `finish`, a point observed `at`, and a rollup all its temporal children
complete. Share that rule with forecasting; neither `recorded`, progress,
planned targets nor an inferred cutoff proves completion. Missing observations
are not known finished. Filtering never changes the scheduler's input. Ordinary
automatic comparison ghosts follow the retained Primary; explicit Snapshot and
Scenario sources keep their independent scope and have no inferred current
completion state. Explicit references to an excluded Primary/Actual retain
the existing unavailable-source error. An empty selection retains its existing
diagnostic. This addition also applies to network selection, without a version
bump; omission leaves selection unchanged (Spec56 §3.2).

`comparison.actual` is `forbidden`, `optional`, or `required`; a Render Context must
provide an Actual set exactly when the selected mode requires it. The `facets` list is
sorted and duplicate-free. `planned` and `actual` remain separate facets, so a Style or
Scene can update only the affected primitive when an observation changes. A View never
changes a planned placement because a delta facet exists.

### 4.2 Closed comparison language

v0.1 comparison bodies use `baseline: primary|snapshot`,
`observationSelection: latest`, and `deltaUnit: calendar-days|working-days`. `baseline: primary`
uses the primary Project's derived planned schedule; `baseline: snapshot` requires a
Snapshot whose resolved `project.id` equals the primary Project ID. `latest` chooses the
observation with greatest positive `sequence` for each resolved Project object; equal
sequences for one object are invalid. Unmatched observations are never planned-comparison
candidates, but may appear through `unmatchedActual`.

`baselineMarks: ghost` (optional; omitted means none, #991) makes a `baseline: snapshot`
comparison draw the Snapshot's placement of each selected item as a baseline ghost in
automatic and lane rows, also under field grouping: View composition adds one
shared-track `snapshot` member (`snapshot:<object>`) beside the primary item, and omits it
for an object the Snapshot lacks. `baseline: snapshot` alone draws no ghost, and explicit
rows name their snapshot items themselves. `ghost` without `baseline: snapshot` or without a
Snapshot in the Render Context is `E_REVIEW_BASELINE_MARKS_SNAPSHOT`. `baselineMarks:
ghost-when-changed` (#991 item 16) draws the ghost only for an item whose Snapshot placement
differs from its current one (any planned date), so an item whose baseline equals the plan gets
no dashed frame. Without a Snapshot baseline or a Snapshot in the Render Context it draws no ghost and
raises no diagnostic (#429), so a Layout profile's `viewDefaults` can offer it to Views that have no baseline.

Draft's explicit `--snapshot <project.yaml>` supplies the same Snapshot Project
role without an immutable SnapshotRef (Spec08 §3.2, #1533). It does not select or
override a View baseline; the rules above apply to either ingress.

`startDelta`, `finishDelta`, and `atDelta` are signed integer distances in the declared
`deltaUnit`: calendar days, or working days in the item's effective calendar (the
object calendar, then the Project calendar). With no calendar, presentation counting
uses all calendar days as working days; it does not invent a weekday calendar or emit
a warning. For finish comparison, planned and observed half-open exclusive endpoints
are compared on the selected basis, so a Saturday exclusive Actual finish and Monday
exclusive planned finish can both denote Friday and yield zero working-day variance.
Positive means later/behind; negative means earlier; zero means equal. A delta is absent,
not zero, if either endpoint is absent or the point/span kinds differ. Point Actuals
compare only with planned points and intervals only with planned spans. Actual intervals
use Core's half-open `[start, finish)` form; a human-facing inclusive finish label never
changes it. Progress is observed only and has no implied forecast or rescheduling effect.

A rollup's displayed planned date range covers its contained View occurrences,
including folded points. Resolve each member span's `endDisplay` using its own
date basis before taking the earliest start and latest finish; point dates are
unchanged. Nested rollup display ranges are already resolved. Comparison-only
tracks and descendants omitted by explicit rows do not extend the range.
This display fact never changes the Core rollup endpoint or dependency ports.

## 5. Projection Pipeline

The View pipeline is separate from styling and scene construction.

```text
Project + Schedule + View Context
              │
              ▼
          Selection
              │
              ▼
    Grouping / Ordering / Window
              │
              ▼
       View Projection (semantic)
              │
              ▼
       Style / Theme / Scene
```

A View Projection contains stable object IDs, resolved temporal placements, comparison facets, lane membership, order, temporal window, and annotation-placement intent. It does not contain rectangles, pixels, paths, fonts, or colors.

## 6. Selection, Grouping, and Ordering

Selection identifies semantic items eligible for presentation. A View MAY select by stable object ID, type, hierarchy, entity reference, profile, or typed extension field.

Relations MAY be shown only when both endpoints are selected. A View MAY retain an omitted endpoint as a non-rendered explanatory boundary, but MUST NOT invent a relation absent from the Project.

Semantic dependencies and explanatory arrows are distinct. A semantic dependency is owned by the Project and constrains or validates scheduling. An explanatory arrow is a View-local presentation annotation; it MAY explain a risk, decision, or causal narrative but MUST NOT create a scheduling constraint.

Grouping creates presentation lanes; it is not semantic containment. v0.1 uses
`{by: objectType}` or `{by: field, field: <declared semantic field path>, missing:
<lane-id>}`. `by: entity` without a field is invalid. `objectType` means normalized
Core shape (`point` or `span`), not an implementation profile name. Ordering is the
tuple `(ordering key, tieBreak, stable object ID)`; missing values sort after present
values in ascending order and before in descending order. The key `source` (also a
`tieBreak`, #991) is the position of the object among the Project's `objects` as the Project
document declares them, not the scheduler's order; descending reverses it, and a group still
keeps its members together.

On a dependency network, Project containment remains distinct from these lanes
(#1727). The projection identifies selected group objects as containers and
closes each selected object's nearest selected container through its Project
ancestor chain. Unselected ancestors are not implicitly selected. A selected
container encloses its selected descendants, not an additional task node;
an empty selected container retains its own header and empty content area.
Selected relations retain their endpoint identity, including group endpoints.
Critical edges use the existing scheduler-derived driving-relation and
critical-endpoint facts, never paint or mere proximity to a critical node.

For a `dependency-network` surface (#416), the existing View `selection`
selects the node objects and the existing global `ordering` supplies their
ordinal order. Projection preserves the resolved order, including direction
and tie-break, independently of the timeline's `rows` mode; timeline explicit
row order is unchanged. Rank layout groups those ordinals without a second network
selector or order declaration. `body.network.nodeLabel.source` optionally
selects `title`, `id`, or the shared Project field-reference object
(`{field: ...}` / `{fieldRole: ...}`). The `network` member is refused on a
`table-timeline` View, even when empty, as `E_RESOURCE_SCHEMA` at
`/body/network`; it requires `surface: dependency-network`.

With no `network.nodeLabel` override, or with its `source` omitted or null,
the node label is its Project title. A field reference uses the existing field binding/default
resolution: a missing, null or unbound field falls back to that object's
title. A present string is used verbatim, including the empty string. A
present non-string value is refused as `E_VIEW_NETWORK_LABEL_SOURCE` at the
label source pointer with the affected object subject; it is not implicitly
formatted. This is node content, not timeline label placement, and Layout
measures and places the completed text.

A grouping with `presentation: header` may declare `header`, a text template for each
group header (literal text, an ordinal in a declared form, the entity title and an entity
field as a secondary title; a first-group variant). The text is View content; its
grammar, ordinal forms and diagnostics are owned by
[Specification 50](50-constraint-driven-gantt-surface-quality.md) section 3.4.

### 6.0 Hierarchy name preservation (#1701)

Presentation grouping does not erase containment levels. A design retains
them in depth-capable hierarchy rows/headers or selects `path` as the member
name in its existing label channel. Ordinary tables use a `source: path`
column; lanes use per-member plot names, not a founder-only lane-table cell.
No new lane, selected item, rollup, or scheduling edge is inferred.

Path segments are immutable source-local object-ID/title pairs, including the
member itself. Snapshot and scenario segments come from their own Project,
not the primary Project. Blank/missing titles use the segment's object ID.
For an explicitly selected path name, omit only ancestor segments represented
by an enclosing, actually displayed header/row/lane for that same source
object. Project-root hierarchy fallback can cover its ancestor; field/entity
groups, object-type groups and ungrouped rows do not cover ancestors by text
or coincident identifier, with one exception: a role-bound field grouping drops the
leading ancestor segments whose title equals its displayed header text (section 6.2,
"Role-bound grouping with parent groups", #1870). Omitted/hidden headers cover nothing. A vertical group tag that gave
way for want of room (Specification 07, #1726) is not displayed: Layout then sets the path column
cells of that group's rows with the full path, covered ancestor included; groups whose tags are
drawn keep the covered path. Keep the leaf.
Explicit hierarchy depth, folding, selection and stable occurrence identities
retain their existing meanings. Depth-limited selection is not overridden to
invent missing rows. Selected points below a finite hierarchy cutoff remain
members of the nearest retained ancestor row, not extra rows (Specification
38 section 2, #1700); Model closes that membership before Layout.

Content normalization closes the name once before Layout; table and plot
carriers consume the same path fact and existing path separator. An existing
`source: path` column without the new explicit path-name selection keeps its
full-breadcrumb behavior. Theme/Style do not select ancestry; Scene/adapters
do not recover it. Fit and pointed absence diagnostics remain Spec50 policy.

### 6.1 Draft relation visibility override (#1299)

For table-timeline spatial resolution, Layout Profile's
`relationRouting.unroutable` supersedes View relation overflow (#1427). View
still owns admission/selection, and overflow retains its network meaning. A
differing effective value produces a migration info; equal suppress values
preserve legacy output. See Spec50 §3.3.

`chrona render --relations none|semantic` overrides only the effective Draft
View's `visibility.relations` mode, before validation and resource identity
freeze. Scalar declarations remain scalar; object declarations retain their
other options. Without the flag, the original declaration and normalization
are unchanged. The override neither writes the authored resource nor mutates
an immutable render-review Context. Scheduling still sees every Core dependency.
`none` omits semantic relation requests before Layout routing; intentional
omission is not `W_LAYOUT_RELATION_SUPPRESSED`. The CLI documents the override
in help and the first-project guide.

### 6.2 Semantic field references (#1559)

Where a View addresses an object field, it MAY use `{fieldRole: responsible}` or
`{fieldRole: phase}` instead of the direct field key. This applies to table and
lane-table column sources, color sources, icon encodings, `rows.laneKeys` and
network node label sources.
Grouping declares `by: {fieldRole: responsible}`, `fallback: objectType|none|hierarchy`
and its ordinary `missing` label. The Project declares the role-to-field map
(Spec 05 §10.1); entity fields and built-in/derived projection sources are not
role targets. Role columns use the design's existing `field` column style.

The primary Project's role declarations determine View policy. An undeclared
role selects grouping's explicit fallback, omits its columns/optional color or
icon encoding, removes the role lane-key component (retaining `byObject`), or
uses the Project title for a network node label.
Evaluation emits one `I_VIEW_FIELD_ROLE_UNBOUND` per role, with `count` and
`sourceRefs` counting affected declarations, not rows. A table or lane-table
*column* whose role is unbound is omitted without that diagnostic (#1870): it is
how a role the Project does not use disappears from a shared design, so a default
render of a built-in design on a Project without the optional `phase` role reports
nothing about it. Grouping, colour, icon, lane-key and node-label references
change how the picture reads and stay reported. Theme roles an omitted column
would have read still count as read (#1616). Ordinary tables with no
remaining column reject with `E_VIEW_TABLE_COLUMNS_EMPTY`; an omitted
`hierarchyColumn` is `E_VIEW_HIERARCHY_COLUMN_UNKNOWN`. No column is invented or
silently substituted. Other target-reference validation remains unchanged.

For the `hierarchy` fallback only, an unbound grouping role is handled by
presenting selected non-group objects beneath their rootmost `type: group`
ancestor from Project containment. Group objects supply header IDs and titles
but are not temporal rows; objects without a group ancestor remain in one
ungrouped section. Intermediate non-group ancestors do not become headers.
This private projection source is not `by: hierarchy`: the authored
`by: hierarchy` tree expansion, depth, and rollup policy remain unchanged.
The handled grouping reference does not emit an unbound-role info diagnostic;
other references to that role (including columns, color, icons, or lane keys)
remain independently diagnosed and handled by their existing rules. A bound
role still groups by its declared field and retains its existing diagnostics,
titles, and output.

A declared role whose field is absent on an item retains the consumer's existing
missing-value/domain behavior, not the undeclared-role fallback. Every item's
role value uses its own source Project's mapping, including Snapshot/scenario
items. Group entity IDs keep existing entity-title resolution; ordinary cells
retain their existing value formatting. Root-group fallback headers use the
corresponding Project group object's title and fields. Grouping, color eligibility and icon
selection retain their existing primary-item scope. Resolve these semantic
facts before Layout; Scene and adapters do not look up roles.

A declared `objectReference` field (#344) uses its source-local semantic binding
(Spec17), not a lookup in the primary Project. Table and lane-table cells display
the resolved target title, or its ID when untitled; `many` displays those titles
in declared order joined by `, ` before the existing column formatting. Ordinary
non-reference values keep their existing formatting/entity-title behavior. Stored
IDs and Project fields are not rewritten, and no renderer resolves a reference.

When a bound field-role grouping is resolved to its Project field, selected
`type: group` summary objects are omitted from those field-grouped rows rather
than receiving the missing-value group as ordinary bars. The projection reports
their omitted count as `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED` under rule R4 below;
member objects retain their field groups. This omission is specific to role-bound
grouping: direct-field grouping and `grouping.by: none` keep their declared behavior.

**Role-bound grouping with parent groups (#1870).** When `by: {fieldRole: R}` resolves
to a Project field (a bound role), four rules fix what the reader sees on a Project that
also declares parent `type: group` objects. They apply to a bound role only: a direct
`by: field` key, an unbound role (`fallback`) and `grouping.by: none` keep their own
rules. No View member is added.

- **R1, header order.** Headers appear in this precedence, first match wins: (1) the
  View's explicit `grouping.order`; (2) `grouping.order.by: earliestPlannedStart`;
  (3) the first appearance of the header among the selected rows in the Project's
  declared object order, so a Project that lists `plat`, `mob`, `data` shows them in
  that order whatever the field values spell; the same declared position is the
  `source` ordering key. The `missing` group (items with no value of the role's
  field and nothing to inherit one from, R3) is last under rules 2 and 3 wherever its
  name would sort; an explicit `order` that lists it places it as listed, and one that
  omits it places it after the listed headers. Rows within a header keep the View's
  `ordering`.
- **R2, row names.** A name that shows the `path` (a `source: path` column, or the
  `path` label content) drops the leading ancestor segments whose title equals, as an
  exact string, the text of the header displayed for that row: the group entity's title,
  else the field value, as the header names it. The member's own segment is never
  dropped, so a path with nothing left shows the object's title. A row under the
  `missing` group keeps its full path. The rule holds for `presentation: header` and
  `band` alike, for plot labels and for table cells. It covers a segment only while the
  header is displayed: where Layout withdraws a vertical group tag (Specification 07,
  #1726) the cells show the full path, and an omitted header (a grouping that
  distinguishes nothing) covers nothing. A header spelled differently from the
  ancestor's title (`Go to market` against `Go-to-market`) is not matched and the
  segment stays.
- **R3, points without the role's value.** A point (gate, milestone) with no value of
  the role's field does not go to the `missing` group when `rows.points` places it
  elsewhere. With `key-row` it leaves the headers for the key row. With `attached`,
  `predecessor` or `group-header` it joins the group of the object it is attached to:
  its `attachesTo` host, else its nearest Project ancestor, that carries the field.
  (`attached` is the default `rows.points`.) With `own-row`, or when nothing supplies
  a value, it is in the `missing` group as before. A View that places its points
  therefore leaves `missing` holding only non-point objects.
- **R4, parent summaries.** A parent group's summary is not a row; its information is
  that of its members. A header shows the union of its members' spans where it shows
  a range at all (the v0.1 header template has no range placeholder, so a header draws
  none). `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED` is reported only when information is
  lost: its `count` is the number of omitted parent groups whose selected descendants
  fall under more than one header (a point the `key-row` takes out of the headers
  belongs to none). A parent whose descendants share one header, or that has none
  selected, adds nothing and emits no diagnostic.

The private root-group context used by the `hierarchy` fallback orders groups
by Project object declaration order when the View declares neither `order` nor
`order.by`. An explicit group `order` or `order.by: earliestPlannedStart`
continues to take precedence. This default does not change other grouping
orders.

Existing View inputs without role references retain their behavior and bytes.
The generic preset intentionally adopts role references: without Project roles,
its visible output falls back, but its required info diagnostics are new input
semantics, not suppressed to preserve an old Scene. Unmodified public Context
outputs remain subject to the public SVG/Scene byte gate.

## 7. Temporal Window

A View selects a temporal window independently from scheduling semantics. v0.1 allows
`{mode: explicit, start: Date, end: Date}`, `{mode: selected-planned, marginDays: N}`,
or `{mode: selected-comparison, marginDays: N}`. Explicit windows are `[start, end)`
with both bounds and `start < end`; derived windows use selected minimum start and
maximum exclusive end. For `selected-planned`, pad each side by
`max(marginDays, ceil(elapsedDays / 10), 1)` Date days, where `elapsedDays` is
the selected maximum exclusive end minus the minimum start (zero for same-date
points). This general rule strictly contains selected marks and preserves larger
authored margins; it does not change Core schedules or depend on fonts, viewport
size or axis units. `selected-comparison` retains its authored non-negative margin.
If padded bounds cannot be represented in the Date domain, diagnose
`E_REVIEW_WINDOW` with the selected dates and object identifiers rather than
wrapping or silently clamping. An empty eligible set is a diagnostic,
never a current-date default.

Before timeline geometry or visibility-index preparation, Layout validates the
completed projection's positive Date window. A still-degenerate or invalid
window reports `E_PRESENTATION_PROJECTION_REQUIRED` at `/projection/window`,
naming the bounds, selected object identifiers and positive-Date-window cause.
Early, direct and candidate-preparation entry paths share this validation;
they must not lose owner-local detail through a generic fallback.

Date-based Views use the Date temporal domain. DateTime View behavior is deferred until a corresponding Core scheduling profile exists. Human-facing inclusive end-date display is a View or renderer concern and MUST NOT alter Core half-open span semantics.

**Bounded-window visibility (#1292, #1812).** The projection retains the selected
window mode as typed provenance; equal dates do not imply equal window policy.
`explicit` and `relative` select the bounded mark-visibility contract in Spec 50.
An intersecting span keeps its original source interval and table row while
Layout completes its visible part. A wholly disjoint span, or a point outside
`[start, end)`, keeps its table row but has no plot facet. Snapshot, scenario,
Actual and missing-Actual facets are evaluated independently without rewriting
Project dates, observation state, progress fractions or delta facts. A point
at `start` is included; a point at `end` is excluded. Derived-window selection
is not changed by this rule.

**As-of-relative focus (#1812).** A timeline View MAY declare
`window: {mode: relative, before: 1w, after: 6w, outside: omit}`. Offsets are
nonnegative integer civil days (`d`) or seven-day weeks (`w`), with no leading
zero except `0d`/`0w`; they are not working durations or calendar months.
At least one side is declared; an omitted side is `0d`. Resolve the exact
half-open interval `[Actual.asOf - before, Actual.asOf + after)`; do not add an
inclusive extra day. Both zero is `E_REVIEW_WINDOW`. A missing Actual `asOf`
is `E_VIEW_WINDOW_AS_OF_REQUIRED` at `/body/window`; Date overflow is a pointed
`E_REVIEW_WINDOW`. No clock, Project date or Snapshot date substitutes for as-of.

Both bounded modes accept `outside: keep | omit`, default `keep` at runtime.
`keep` retains today's rows and clipping. `omit` retains a row only when one of
its selected temporal source occurrences intersects the window, using the same
source visibility closure as mark clipping, not paint, labels or Theme. Any
Primary/Actual/Snapshot/Scenario track can retain its row; a derived missing-
Actual tick alone cannot. Preserve authored row/lane IDs and lane membership;
compact only the admitted row geometry. Group headers remain for admitted rows
or folded occurrences, not empty outside-only groups. Keep the complete source
projection and relations for omission proofs. All-outside source sets may have
zero geometry rows; do not invent a row or extend the window.

The initial truthful relation fallback is the existing typed suppression with
`W_LAYOUT_RELATION_SUPPRESSED`, identifying each affected relation and its proven
outside source/endpoint. It is documented and observable, never a silent dropped
edge. A clipped edge is not a semantic port, and existing paired routing stubs
are not window-continuation stubs (Spec50). The guide explains this fallback.
`relative` and the new `outside` member are timeline-only; reject them on a
network View rather than ignoring them. Existing network declarations are
unchanged. Derived window modes do not accept `outside`.

### 7.1 Named periods (#582)

Alternatively, `periods: {select: all}` selects every Project period in Project
declaration order (#1560), including an empty selection when none are declared.
The closed selector MAY carry `label` with the same grammar as an explicit
entry; that label intent applies independently to every selected period.
`label: {}` may inherit `viewDefaults.periodLabelPresentation`, with explicit
View members taking precedence. No label member means bands without labels.
The selector introduces no per-period variant, inferred dates or Theme policy.
Explicit id-list ordering, duplicate/unknown-id failures, absent selection and
the dependency-network exclusion remain unchanged. Expansion occurs after
Project period resolution, before Layout receives ordinary completed period
intent; Scene and adapters do not implement selection.
The shared named-preset View selects all periods and requests their labels.
It also declares the existing kind bindings for span `note`/`risk` at
`planned/end` and point `note` at `planned/at`, all with purpose `note`.
These generic bindings do not require an Actual input; a project-specific
View may explicitly choose another existing facet/endpoint. Kind matching,
selection, overrides and placement policies retain Specification44's rules.

A `table-timeline` View MAY select named Project periods (Spec 05 §12.1) with `periods: [{id}]`, each drawn as a band across the plot rows over the period's dates. The selection owns only which periods are shown and in what order (the order is the drawing order); the period's dates are a Project fact and its colour, stroke, opacity and pattern are Theme role `period-band` (Spec 07), its geometry Layout's (Spec 50 §3.4). The band is clipped to the View window and never extends it: a period with no extent left draws nothing and is recorded as the Scene diagnostic `I_LAYOUT_PERIOD_OUTSIDE_WINDOW:<id>`. An id the Project does not declare is `E_VIEW_PERIOD_UNKNOWN` (pointer `/body/periods/<i>/id`; the message lists the declared ids) and a repeated id is `E_VIEW_PERIOD_DUPLICATE`; nothing is skipped silently. The member is optional and additive in `chrona/view/v0.28`; a `dependency-network` View, which has no timeline, MUST NOT declare it. A View without `periods` renders as before.

A selected period MAY also declare `variant`, a `common-v0.1` `slug`. It chooses the paired Theme roles `period-band:<variant>` and, when a label is consumed, `period-label:<variant>` (Specification 07). The variant is View-local presentation intent, not a Project period identifier or a Theme lookup fallback. Without it, the existing unsuffixed roles and output apply. The optional member is additive to the current View version under Specification 56 §3.2.

A selected period may carry `label: {placement, overflow?, text?}`. `placement` is `top` (at the plot's top edge), `bottom` (at its bottom edge) or `inside` (centred in the band); the label is the View's `text` override when it declares one (#871; one to eighty characters, shown for this View only), else the period's `title` (its identifier when absent), centred on the band's visible extent. `overflow` is `suppress` (omit the label and record `W_LAYOUT_LABEL_SUPPRESSED`) or `visible-overflow` (the default: place it at the preferred position and record `W_LAYOUT_LABEL_OVERFLOW`) when no collision-free position exists; a label never silently overprints a mark. Absent `label` draws the band alone.

A Detail Profile legend entry for a period MAY declare `sourceRef` as that
Project period's id. The binding is valid only when the same period is selected
by this View, exactly once, and the entry `role` equals that period's selected
band role (`period-band` or `period-band:<variant>`). Unknown, unselected,
ambiguous, or duplicate sources fail with `E_REVIEW_LEGEND_PERIOD_SOURCE` at
`/body/legend/<index>/sourceRef`; a mismatched role is
`E_REVIEW_LEGEND_PERIOD_ROLE` at `/body/legend/<index>/role`, both attributed to
the Detail Profile rather than the View. They are not ordinary unsourced keys.
The source identifies
the Project period, while the role controls visual selection. Existing
`wording.legend` remains role-wide and therefore overrides the labels of all
entries with that role, including source-bound period entries.

### 7.2 Axis band fills (#490)

A `table-timeline` View MAY give a fixed-unit `axis.tiers[]` band tier `fillScale: {scale, key, containingTier?}`. `key: alternating` selects Theme slots `"0"` and `"1"` by the natural interval ordinal's parity; `key: interval` selects its canonical decimal ordinal. An optional `containingTier` names another declared, coarser fixed-unit band tier and selects by the unique natural interval containing this interval. The View names the Theme scale and the source rule; Layout resolves interval identity, and Scene receives the resolved paint without changing geometry. A tier without `fillScale` renders as before. See Presentation Specification 60 for interval, Theme mapping, and diagnostic rules.

### 7.3 Deadline marks (#822)

A `table-timeline` View MAY declare `deadlines: {show: slipped | all}` to draw
each object's Project `deadline` (Spec 05 section 9). The date is an inclusive
promise. Its **tick** is at the boundary after that calendar day, centred on the
object's primary planned/forecast mark. A missed promise adds a **run** over
`[deadline + 1 day, inclusive finish + 1 day)`, using the completed Core
boundaries of Spec04 §10. Thus finishing on the deadline draws no late stub;
a one-day-late span or point has one late day. Point judgments still use `at`;
span judgments use exclusive `end - 1 day`. `slipped` selects missed promises;
`all` selects every promise, with a run only when missed. Slipped and kept
differ by shape, not only colour. Core owns this verdict (`deadline_statuses`),
View selects, Project owns the date, Theme owns paint and reach (Spec07,
`deadline-mark`), and Layout owns geometry (Spec50 §3.4). Without the optional
caption below, no text is drawn.

In explicit forecast mode (§8.5), use the forecast finish for an object with a
selected primary temporal occurrence in the final rows or folded members.
Combined primary/Actual members qualify; Actual-only, Snapshot/scenario and
non-temporal context headers do not. All other Project objects retain their
planned finish. Resolve this source choice before Layout window clipping or
paint admission: geometry cannot change the deadline verdict. Repeated primary
occurrences consume one per-object Core status, also used by `W_DEADLINE` in
Project order. Hidden deadline overrides suppress marks, not the warning.
Tick and run retain the existing `deadline-mark` paint. Estimated forecasts
retain §8.5's delta/legend convention, not a new estimated stroke.

A timeline deadline whose completed tick boundary is outside the View window
draws nothing and is recorded as `I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:<object>`.
Layout clips a visible late run to the plot; clipping never changes the Core
verdict or warning. A primary point folded into a group header hosts the same
tick/run as an ordinary point; Layout reserves its complete painted envelope
before labels. A Theme omitting the selected role fails with
`E_THEME_ROLE_REQUIRED` at `/body/roles/deadline-mark`. The member remains in
`chrona/view/v0.28`; no source syntax changes. Without shown deadlines, geometry
is unchanged. A Detail Profile legend entry with role `deadlineMark` explains it.

A `dependency-network` View MAY declare the same `deadlines` member. It shows
a node-attached deadline footer, not a date-positioned timeline run. View
closes the selected node's promised date as ISO `YYYY-MM-DD`, its Core verdict
and optional bound caption before Layout. A kept deadline has a vertical tick;
a slipped deadline has an L-shaped indicator with a horizontal foot. This is a
categorical shape distinction: neither its position nor length encodes a date
or duration. The ISO date is always visible for a shown deadline; an opted-in
slipped caption follows it, separated by one space. Unit words remain author
copy. No timeline window hides a network deadline or produces an outside-window
notice. Layout measures the entire footer before sizing nodes, ports and route
obstacles; natural growth uses existing network overflow diagnostics, not a
post-route overlay. Only selected primary nodes acquire footers. Absent
deadlines/hidden overrides preserve the old node exactly; no new schema version,
generic annotation scope or network surface redesign is introduced.

Optional `deadlines.overrides` maps Project object ids to `{show: all | slipped | hidden}`.
The per-object rule replaces `deadlines.show`, including allowing a kept deadline
under a global `slipped` rule. `hidden` omits the object's mark and caption but
does not remove its Core deadline warning. Unlisted objects inherit the global
rule; an empty map is identical to an absent map. Overrides neither select an
otherwise unselected object nor synthesize a deadline for an object without one.
An undeclared object id fails with `E_VIEW_DEADLINE_OBJECT_UNKNOWN` at
`/body/deadlines/overrides/<id>` before filtering, even for `hidden`.
The entire `deadlines` fragment remains one View-default override unit.
These additive rules retain View v0.28. The former folded-only omission and
`I_LAYOUT_DEADLINE_FOLDED` are retired for drawable folded occurrences; no
compatibility switch preserves that omission.

An optional `deadlines.caption: {template, format?}` (#1397) draws copy beside
each slipped run; the bare tick/run treatment described above draws no text.
The template is a shared `literalCaption` string and accepts only `{daysLate}`
plus escaped literal braces `{{`/`}}`. Unit words and locale are author text;
inline role marks and figure references are not admitted. Malformed templates
fail with `E_VIEW_DEADLINE_CAPTION_TEMPLATE` at
`/body/deadlines/caption/template`. `format` uses shared `countTextFormat`
(digits by default, English words, kanji or formal kanji); its existing invalid
and range diagnostics point to `/body/deadlines/caption/format`. Presentation
formats the Core's existing late-day count before Layout; no new figure scope
or domain date calculation is introduced. Kept deadlines have no caption.
Absent caption preserves existing output. Theme text treatment is Spec07;
placement, optional omission and counted diagnostics are Spec50 section3.4.
On a dependency network, that same already-bound caption is part of the
measured footer instead of the timeline's late two-anchor placement. The node
grows for its complete date/caption content; it is not silently dropped and
does not produce `I_LAYOUT_DEADLINE_CAPTION_DROPPED`.

### 7.4 Heading templates (#991)

Both native Views MAY declare `heading: {title?, subtitle?, dateForm?}`. Each of `title` and `subtitle` is a template of literal text and the closed placeholders `{project}` (the Project title), `{asOf}` (the Actual Set's as-of date, formatted by the shared as-of rule below) and `{calendar}` (the Project's default calendar **title** when that calendar declares one, else its **id**; #1026). `{{` and `}}` are literal braces; any other brace use is `E_VIEW_HEADING_TEMPLATE`. The grammar is the group-header template's (section 6, #583) with this placeholder set. A fact the Project lacks (no as-of date, no default calendar) renders as empty text. Without `title` the title is the Project title; without `subtitle` there is no subtitle line, and a View without `heading` renders as before. The content layer composes the text; the title slot measures it as a stack of a `heading` run and a `subtitle` run, so the slot grows by the subtitle line; Layout places the subtitle under the title and Scene emits it as `subtitle-text` in the Theme's `subtitle` typography role (a Theme without that role fails with `E_THEME_ROLE_REQUIRED`). This same heading contract applies to a `dependency-network` whole-title host (#1841); no surface-specific title substitution is permitted. The member is optional and additive in `chrona/view/v0.28`.

The heading `{asOf}` and as-of marker share one locale date formatter (#1810).
An explicit marker `date` selects its form/name table for both; otherwise use
the heading's `dateForm`, or `localized-date` in the context locale. Sharing
the format does not add a date to an explicitly declared marker that omits
`date`; it remains label-only. Marker copy and Theme case treatment remain
independent wording. A missing semantic
heading fact still substitutes empty text, but emits
`W_PRESENTATION_HEADING_FACT_MISSING` naming the fact and heading source
pointer. Invalid/unknown placeholders and figure references retain their
existing errors; this warning does not soften admission.

For independent heading-part sources (Spec 33, #1239), both native surfaces
resolve the View's heading into named parts. A dependency-network profile without
a whole-title host selects this mode; a whole-title host consumes the same
composed View heading. Only allocated parts require their typography roles, and Layout
reports unallocated nonempty copy without measuring it.

A heading MAY also declare `kicker` (#1189), a template using the same facts,
grammar and `dateForm`, above the title in the Theme's required `kicker`
typography role. Content normalization retains named kicker/title/subtitle
runs. Layout measures and places them as one completed block: the measured
envelope contains every text bound, including actual font-baseline offsets
and the Theme's declared kicker gap. Without `kicker`, existing title/deck
measurement, coordinates and output remain unchanged. This is an optional
addition to `chrona/view/v0.28`, not a new schema version.

**Conditional heading parts (#1608).** A kicker, title or subtitle may instead
be an ordered list of `{text: <template>, omitWhenZero?: <count figure id>}`.
Parts concatenate verbatim; no spaces, separators or placeholders are invented.
`omitWhenZero` reads a declared global count's raw integer, not its formatted
text. At zero Layout omits that part silently before measurement; otherwise it
binds its existing template normally. Unknown guards are `E_VIEW_FIGURE_UNKNOWN`,
group-scoped guards are `E_FIGURE_SCOPE_UNAVAILABLE`, and non-count guards are
`E_VIEW_FIGURE_INVALID`, at the guard reference. Guards participate in the same
deferred Layout-count closure as template reads. An entirely omitted heading
member contributes no text. String shorthand retains its existing behavior.
The shared heading schema admits this optional form in place for both Views and
Layout `viewDefaults` (Spec 56 §3.2); Scene and adapters receive only completed text.

**Presence conditions on heading parts (#1880).** A heading part may also declare
`presentWhen: actualSet | snapshot`. The part is kept only when the render supplies an
Actual Set (`actualSet`) or a Snapshot (`snapshot`, a baseline Project or package); otherwise
it is omitted silently when the heading is composed, before figure binding and text
measurement, as an `omitWhenZero` part is at zero. A part may declare both, and both must
hold. A part that is omitted for lack of data reports no missing-fact warning for the
`{asOf}` it would have read (`W_PRESENTATION_HEADING_FACT_MISSING`). Any other value is a View/Layout schema
error. A heading whose parts are all omitted contributes no text. String shorthand and
parts without `presentWhen` are unchanged.

### 7.5 Slot caption copy (#1100)

A View MAY declare `slotHeadingText: {<Layout slot node id>: <literal copy>}`. Each target must be a slot
with a heading in the resolved Layout Profile, including an optional slot absent from this render. Copy is
one to eighty characters without control characters, not a template. An unknown, container or headless
target refuses the render with `E_VIEW_SLOT_HEADING_TARGET` at `/body/slotHeadingText/<escaped node id>`;
the message names the target and valid headed IDs. Layout completes the selected text using the existing
heading typography, placement, transform and overflow rules (Spec 33); the caption's inline bounds follow
its selected text, without mutating the profile, slot allocation or non-caption geometry. An absent optional
slot still draws nothing. Without this optional v0.28 member,
or with an empty map, the profile's copy and output remain unchanged.

### 7.2 Derived figures (#586)

**Restricted counts (#1880).** A `count` figure may declare `objectTypes` (non-empty list of
domain object types), `temporalKind` (`point` or `span`, the planned shape) and, with the
`groups` source only, `excludeUnassigned: true`. The restrictions narrow the distinct
selected Primary/combined identities before any source is counted, so `selected`,
`recorded`, `behind` and the other sources count only the matching objects; `groups`
counts the distinct nonempty group identities of the matching objects, and
`excludeUnassigned` also leaves out the group that collects objects with no grouping value
(the grouping `missing` fallback, whether a plain field grouping or a role-bound one).
Omission keeps today's count of every selected object and group. A group-scoped figure
applies the restriction to the members of the current group. `placedNotes` cannot be
restricted, and `excludeUnassigned` with another source is `E_VIEW_FIGURE_INVALID` at the
property (`/source` for `placedNotes`). Slot-binding figures (`bindings`) do not take the
restrictions.

**Reusable heading counts (#1346).** Heading
parts additionally admit existing `{figure:<id>}` markers. Slot headings may
declare `template` instead of literal `text` (Spec33); `slotHeadingText` stays
literal. Unknown/malformed/scoped references retain existing diagnostics and
exact pointers. `count` adds global-only `groups` and `placedNotes`. Selected
items are distinct Primary/combined object identities, not ghost/scenario or
repeated appearances; groups are distinct nonempty group identities in those
selected memberships. Placed notes are Spec33 completed narrative occurrences,
not selected Project notes. This late source is table-timeline-only and read
only by heading parts/slot captions; other consumers refuse it with
`E_FIGURE_LAYOUT_SCOPE` at their reference. Unused late figures still resolve.

Optional `figureFormats` maps declared count-figure IDs to closed text formats.
Layout `viewDefaults.figureFormats` offers whole-member replacement; a View
map, including `{}`, replaces it. Malformed shapes/options retain the schema
diagnostic. Unknown IDs or non-count targets are `E_VIEW_FIGURE_FORMAT_INVALID`
at that entry. Omission keeps decimal
text. Forms: `digits` (`minimumDigits: 1..80`, default1), `english-words`
(`capitalize`, default false), `kanji`, `kanji-formal`. Zero is `0`, `zero` or
`〇`; padding never truncates. English uses hyphenated tens, spaces between
scale groups, no comma or “and”, names through quintillion (0..10^21−1).
Kanji forms share existing Presentation digit/ten name tables (0..99), not
a new Core/localization table; ordinal ranges do not change. Outside available
names is `E_VIEW_FIGURE_FORMAT_RANGE`, with value/form/range, not silent digits.
Each formatted text read retains its figure identity for attribution.
For a late candidate's placedNotes read this is admission rejection, not a fatal error on the
possible upper count: a lower representable self-consistent count may exist.
If no admitted candidate closes, Spec33's failure includes that range evidence.
Template consumers use the selected format; Summary metrics retain raw integers
and their own format. Validate every format declaration's shape and target
eagerly, but require number names only when a template reads it; an unused
count remains a raw integer. Theme's existing text treatment applies afterwards.

A View MAY declare `figures`, an array of derived figures that the Core resolves (Spec 05 §12.2) and a consumer shows by name. Each has a unique `id` (no braces, whitespace or control characters: `E_VIEW_FIGURE_INVALID`; a repeat is `E_VIEW_FIGURE_DUPLICATE`) and one closed `kind`: `daysUntil {from?, to, days?, calendar?}`, `daysIn {period, days?, calendar?}` or `count {source, scope?, objectTypes?, temporalKind?, excludeUnassigned?}`. A fact (`from`, `to`) is exactly one of `asOf`, `{period, side: start | end | last}` or `{object, endpoint: at | start | end}`; `from` defaults to `asOf`. `last` is the period's exclusive end minus one calendar day, not its last working day (Spec 05 §12.2). `days` is `calendar` (the default) or `working`; `calendar` names the Project calendar a working count uses (the Project default when omitted) and is a dead declaration, `E_VIEW_FIGURE_INVALID`, with calendar days. Nothing else is accepted: no expression, no operator, no field name, no other kind or fact.

Every declared figure is resolved after scheduling, whether or not a consumer shows it. A fact that cannot be read refuses the render with all findings (`E_FIGURE_PERIOD_UNKNOWN`, `E_FIGURE_OBJECT_UNKNOWN`, `E_FIGURE_ENDPOINT_UNAVAILABLE`, `E_FIGURE_ASOF_MISSING`, `E_FIGURE_CALENDAR_UNAVAILABLE`; the message names the figure, the fact and what is declared): a figure is never blank, zero or guessed. A Summary Profile metric shows a figure with `source: {figure: <id>}` (Spec 46); an undeclared Summary figure is omitted with `I_SUMMARY_FIGURE_UNBOUND` under #1344, while other template consumers retain `E_VIEW_FIGURE_UNKNOWN`. The member is optional and additive in `chrona/view/v0.28`; a View without `figures` renders as before except that explicitly approved Summary omission.

A `daysUntil` figure MAY declare `scope: group` (omission or `global` resolves once).
The additional fact `{group: firstPlannedStart}` requires that scope. View projection gathers
the earliest selected Primary planned start or point in each rendered group; Core receives only
that date, not projection objects. Group figures are keyed by group identity and figure identity,
separately from global values. Plain and role-marked group headers resolve `{figure:<id>}` in their
current group. A global consumer such as a Summary Profile cannot select a group-only value
(`E_FIGURE_SCOPE_UNAVAILABLE`). No projected groups is `E_FIGURE_GROUP_UNAVAILABLE`; a group
without a selected Primary start/point is `E_FIGURE_GROUP_START_MISSING`, not zero. Neither
comparison ghosts nor duplicate lane appearances change the selected dates.

`kind: count` selects one closed `source`: `selected`, `recorded`, `dueUnobserved`,
`notYetDue`, `unavailable`, `missingActual`, `knownFinishVariance`, `behind` or `ahead`.
It accepts `scope: global | group` (global when omitted), but no date facts, calendar or day unit.
One projection-owned producer supplies these facts to both figures and existing Summary metrics:
selected Primary items, not row occurrences or comparison ghosts. The four state sources count
the already-projected observation state. `missingActual` counts due-unobserved items but is
unavailable without explicit Actual as-of; that is `E_FIGURE_COUNT_UNAVAILABLE`, not zero.
Known finish variance counts non-absent deltas, including zero; behind/ahead count strictly
positive/negative observed deltas. They are not critical-path membership, forecast or project
slippage. Count figures accept Summary `count` or `text`, never `date` or `signedDays`.

A period label MAY declare `template` instead of its literal `text`: a closed grammar of
`{figure:<id>}` and `{{`/`}}` brace escapes. Both sources together are `E_VIEW_PERIOD_LABEL_SOURCE`.
Literal `text`, including figure-like strings, is unchanged. A malformed template is
`E_VIEW_FIGURE_TEMPLATE`; an undeclared figure is `E_VIEW_FIGURE_UNKNOWN`; a group-scoped
reference is `E_FIGURE_SCOPE_UNAVAILABLE`, all at `/body/periods/<index>/label/template`.
Presentation resolves the global integer before Layout measures and places the caption.

## 8. Comparison Views

A comparison is a named relation between independently identified states; it is not a mutable field added to every Project object.

### 8.1 Current versus Snapshot

Current-versus-Snapshot compares the Primary Project with an immutable named Snapshot. A Snapshot MAY ultimately be represented by a Git ref. Alignment uses stable project-local IDs. A missing object is a comparison result, not an instruction to create or delete an object.

### 8.2 Plan versus Actual

Plan-versus-Actual compares planned placements from the Primary Project or named Snapshot with independent Actual observations. An observation has exactly one occurrence shape (an interval's `finish` is the exclusive end, the day after the last day, and MUST be after its `start`; otherwise the Actual Set is rejected when read as `E_ACTUAL_FINISH_NOT_AFTER_START` at `/body/observations/<i>/actual/finish`, naming the observation id and suggesting `finish: <start + 1 day>`): a point `at`, or an interval with one or both of `start`/`finish`, optionally progress. It has a positive `sequence`; v0.1 selects the latest sequence. Actuals MUST NOT automatically change planned dependencies, duration, forecast, or schedule.

A selected span Actual with a `start` and no `finish` is an in-progress observation, independently of its progress value (including 0, 1, or no progress). When the Actual Set supplies an `asOf` strictly after the start, Layout draws its Actual facet from the observed start through that cutoff and the existing Theme `progressFill` policy may fill the declared fraction. The cutoff is not an Actual fact: implementations MUST NOT write or expose it as `actual.finish`. An absent start remains incomplete and cannot produce an Actual bar. A started Actual without an `asOf` uses the existing open-Actual as-of-required diagnostic/absence; a zero-length cutoff at/before start keeps its existing invalid-cutoff behavior (#1582).

The View Projection MAY expose planned and actual endpoints, start/finish delta, progress, absent observation, and unmatched observation. Whether an actual delay triggers rescheduling belongs to a future scheduling or application policy.

### 8.3 Comparison Alignment

Comparison alignment MUST use stable IDs. A renamed title, regrouped object, or changed visual placement remains the same comparison subject. An unknown reference MUST produce a comparison diagnostic and MUST NOT be matched by text similarity.

### 8.4 Comparison truth table

| Baseline placement | Selected Actual | Requested facet | Result |
|---|---|---|---|
| span `[S, F)` | interval | `startDelta`, `finishDelta` | Signed calendar-day difference for each present endpoint |
| span with Actual start and no finish | in-progress interval through Actual `asOf` | `finishDelta` | Absent before the planned exclusive end; otherwise signed calendar-day difference from that end to `asOf` |
| point `A` | point `at` | `atDelta` | Signed calendar-day difference |
| span | point | start/finish delta | Absent facet and `VIEW-COMPARISON-ENDPOINT-KIND` |
| point | interval | `atDelta` | Absent facet and `VIEW-COMPARISON-ENDPOINT-KIND` |
| span with planned exclusive `end` on/before Actual `asOf` | no resolved observation | `missingActual` | `true`; Actual/delta facets absent |
| point with planned `at` on/before Actual `asOf` | no resolved observation | `missingActual` | `true`; Actual/delta facets absent |
| planned due endpoint after Actual `asOf` | no resolved observation | `missingActual` | unavailable, not `false` or `true`; no missing-Actual mark |
| any | selected observation exists | `missingActual` | `false`, including an incomplete observation |
| any | no Actual `asOf` available | `missingActual` | unavailable; no due-state inference from the local clock |
| any | multiple observations | any | Greatest `sequence`; duplicate sequence is invalid |

`finishDelta` uses the canonical exclusive endpoint; display inclusivity never changes it.
The View derives one typed observation state (`recorded`, `due-unobserved`,
`not-yet-due`, or `unavailable`) from the selected observation, canonical
planned due endpoint and explicit Actual `asOf`. Equality with `asOf` is due.
All table, summary and Layout missing-Actual consumers use this projected
state; a future unobserved item must not be called “Recorded”. An observed but
incomplete Actual remains recorded, not missing. A started span Actual with no
finish is displayed through the explicit Actual `asOf` cutoff and uses that
cutoff for finish variance once it passes the planned exclusive end. This does
not synthesize an Actual finish or change missing-observation policy.

A table column MAY declare `missingBy` (optional, #991): the text of an absent value by the item's observation state, each of `inProgress` (a span with an Actual start and no finish), `dueUnobserved`, `notYetDue` and `unavailable` taking `blank`, `em-dash`, `unknown` or an author-chosen literal `{text}` (#1288: one to eight characters with no control character, drawn exactly as written in the column's text role); a state not named keeps the column's `missing`, which takes the same `{text}` form. `affixes.missing` is unchanged and wraps whatever the absent text is, in every absent state, so it is not the way to mark one state only. A Delta column can thereby leave unobserved items blank and show a dash for in-progress ones. It changes only the text of an absent value (affixes still wrap it); without it every absent value reads `missing` as before. It applies to automatic and explicit rows, not to the fixed lane table.

`comparison.missingActualScope` (optional; omitted or `due-unobserved` is the behaviour above,
#991) selects the scope of the `missingActual` facet; it does not change observation truth. A
started span Actual is recorded and is drawn as an Actual facet through `asOf`, never as a
`missing-actual` mark, regardless of this member or progress. Its finish variance is absent before
the planned end and uses `asOf` once that end has passed. Genuinely unobserved work remains
subject to the selected missing-Actual scope. The selected Actual with an invalid zero-length
cutoff remains absent with its established invalid-open-Actual diagnostic (#1582).

### 8.5 Explicit forecast presentation (#1634)

Specification 04 §17.1 defines the separate forecast schedule. Only an explicit
Render Context forecast request activates it. Original planned placements,
Actuals, observation state and observed variance remain distinct facts; progress,
source-plan figures, ordering and periods are not silently reinterpreted as
forecasts. Deadline comparison alone explicitly selects the displayed forecast
finish under §7.3; source-plan scheduling/warnings remain plan-based outside
this opt-in render. This is not automatic Actual-driven mutation.

For selected primary temporal items represented in the View's rows, the forecast
replaces the ordinary primary mark. Comparison-only members and context-only
hierarchy headers are not additional primary items. Forecast marks retain the
Project object identity, carry purpose `forecast`, and use the existing planned
paint vocabulary; no Theme needs a copied per-project forecast style. Layout
uses their completed geometry for tracks, packing, ports and dependency routes.
It does not pack forecast bars using stale original intervals. Label-window
admission, mark visibility and lane-label preflight use those same active
intervals, not the stale planned facet. Source-date
bindings and explicitly planned annotation anchors remain source-plan facts.
Critical/float/driving decoration may use computed forecast analysis only; absent
analysis is not borrowed from the original plan.

Forecast comparison uses the supplied Snapshot, or the original primary plan if
none was supplied. A selected item the supplied Snapshot does not contain is
**new** (#1755): it draws normally, its baseline distance is absent (not zero
and not invented), its delta cell and label read `new` (wording key `marker.baselineNew`; `新規` in `ja-JP`) without `*` or variance
paint, and the forecast skips its baseline comparison. A Snapshot object with no
current counterpart that the View's selection would show is **removed**: in an
automatic-row View whose ghosts are shown (always in forecast mode;
`comparison.baselineMarks` `ghost` or `ghost-when-changed` otherwise) it draws
as a baseline ghost row whose title ends `(removed)` (`marker.baselineRemoved`; `(削除)` in `ja-JP`); otherwise
(hidden ghosts or explicit rows) one `I_BASELINE_OBJECT_REMOVED` information
diagnostic lists it. The same new/removed rule applies to ordinary Snapshot
comparison. `E_FORECAST_BASELINE_UNAVAILABLE` remains only for a displayed item
without a forecast schedule or whose baseline kind differs (span versus point).
For this explicit mode, `finishDelta` presentation consumers select the separate
forecast comparison fact: forecast exclusive `end` minus baseline `end`, or `at`
minus baseline `at` for points, using the View's `deltaUnit`. Both table source
forms, plot text and variance paint use that same selection. Observed variance
facts and figures remain unchanged. Unfinished values append `*` (for example
`+4d*`); completed values do not. Completion follows Spec04 §17.1, not progress.
Rollup estimates reflect unfinished descendants.

A supplied Snapshot remains a separate baseline ghost. The forecast comparison
layer requires it independently of the ordinary Actual-comparison baseline.
Use a declared `ghost` policy; otherwise forecast mode requires a visible ghost
for the supplied Snapshot, even when its placement equals the forecast. This
explicit forecast-only override of the ordinary omitted/changed-only policy
does not create a ghost without a supplied Snapshot. It keeps the owner's
baseline-visible promise without changing ordinary View defaults.
Do not emit a duplicate ghost already represented in the same explicit row.
Explicit rows must provide a compatible baseline track or refuse the forecast.
Derived windows include forecast endpoints and drawn baseline ghosts; explicit
windows remain authoritative and retain ordinary clipping diagnostics.

The forecast primary owns the member-name label for its object occurrence.
A paired Snapshot ghost has no member-name label, independently of its visible
temporal paint; it still carries its baseline mark and provenance. View
projection declares this occurrence eligibility before Layout, including in
automatic, explicit, lane and folded compositions. Layout measurement/admission
honours it without inferring forecast/source policy. The primary title keeps
the existing View visibility/overflow rules; its required forecast delta is
independent and remains required. This does not remove intentional repeated
primary occurrences or alter ordinary non-forecast comparison labels.

Forecast requires a table-timeline View with a declared per-item `finishDelta`
channel and a Layout legend slot. Unsupported presentation is
`E_FORECAST_PRESENTATION_REQUIRED`, with the missing capability named; do not
invent a slot, change View selection, unhide rollups or synthesize adapter text.
The content layer replaces the ordinary planned legend candidate with a
`forecast` candidate, or adds it when absent, labelled `Forecast (* estimated)` by default.
`wording.legend.forecast` may provide declared wording; its swatch reuses planned
paint. Do not leave a misleading current-plan key for the replacement bars.
Final painted-occurrence filtering follows Specification 60 §4: if encoding
replaces every forecast mark's base paint, its scale keys replace this base
swatch too. If a completed visible delta still draws its estimated `*`, keep
the forecast entry as a text-only explanation: the same required wording,
without a swatch or swatch-label gap (#1810). Its witness comes from the typed
estimated-delta fact on final text placements, never text parsing or available
forecast sources. Reserve the candidate before Layout choice; final composition
may remove its swatch or the unused entry, not restart geometry. This explanation
claims no category ink. Source capability checks still require the declared
delta channel and legend slot.

The built-in `column.finishDelta` header names the displayed delta's reference:
`column.finishDeltaPlan` for Actual/current-plan or forecast/primary-plan,
`column.finishDeltaBaseline` for forecast/supplied-Snapshot. Keep the authored
wording-key identity until that reference is known. Literal headers, other
wording references and explicit wording overrides retain their authorship.
The comparison calculation and working/calendar-day units are unchanged.

Every selected primary temporal item needs a complete, visible forecast delta.
Table cells use measured full comparison text; plot deltas are independent
required text requests, not optional parts of a suppressible title. Reuse
Layout's existing required-text/atomic-table refusal behavior if they cannot
fit, including under an explicit window; never silently ellipsise away `*`,
suppress a required delta, or remove a row to obtain success. Optional titles
keep their existing policy. Scene and adapters receive completed placements and
paint only; they do not calculate dates, choose fonts or place the legend.

An explicit `outside: omit` is source-temporal admission, not a fit escape:
Layout records the original window absence before measuring or requesting
forecast text for an omitted occurrence. A plot delta with an outside temporal
anchor uses that typed absence; it is not a spatially suppressed required
label. Retained in-window forecast text and visible table cells still require
their full text and retain the existing refusal. Source-channel admission is
unchanged; a window does not invent an undeclared forecast destination.

Channel coverage is per selected temporal occurrence, not merely the presence
of a delta column somewhere in the View. An explicit row's table channel
covers its `tableSubject` only; another primary item in that row needs the
declared plot delta channel. A point folded into a group header has no table
cell: with a declared plot delta channel, Layout places its independent required
delta on that header track and includes its full footprint in header packing.
It retains forecast mark identity and the same pre-route required-text guards
as a row delta. A table-only folded point, or another uncovered occurrence,
is `E_FORECAST_PRESENTATION_REQUIRED` naming that occurrence and missing
channel. Do not invent a table row or an undeclared plot destination, unfold
the point, or omit its delta. An eligible but spatially unplaceable declared
channel still uses the required-text refusal, not a capability error.

## 9. Annotations and Layout Intent

Semantic annotations remain Project data and are selected with their anchors. Presentation annotations are View-local callouts, highlights, notes, or explanatory arrows. They MAY anchor to a selected object, relation, group, or temporal coordinate. The View owns the stable anchor and logical placement preference; Layout owns every concrete offset, coordinate, collision decision, and connector route. Scene projects completed Layout geometry and Rendering serializes it. Deleting a presentation annotation MUST NOT alter a Project object, semantic annotation, or dependency.

### 9.1 Presentation annotation intent

A presentation annotation has a stable View-local ID, one typed anchor, a purpose, and
a logical placement preference. It is not a free coordinate blob. This
legacy shorthand normalizes to an ordered candidate:

```yaml
annotations:
  - id: supplier-risk
    purpose: callout
    anchor: {kind: object, id: firmware}
    placement: {side: above, alignment: end}
    text: "Supplier confirmation pending"
```

Initial `purpose` values are `callout`, `highlight`, `note`, and `explanatory-arrow`.
An explanatory arrow additionally has `source` and `target` typed anchors. It is
projected with source kind `explanatory-arrow` and can never satisfy, replace, or alter
a semantic dependency. A missing anchor produces a View diagnostic; no title or
geometry-based recovery is allowed.

View selection, grouping, hierarchy expansion, visibility, and annotation anchoring are semantic inputs, not renderer geometry. An annotation has one source (`text` or a stable Project annotation reference), a typed anchor, and an ordered candidate list. A Project reference inherits narrative text and object identity; View owns facet, endpoint, purpose and placement. The anchor endpoint is `start`, `end`, `finish`, `at` or `body`; `end` is the canonical spelling of a span's end and `finish` its alias, and the two produce the same Scene. A referenced Project note is not duplicated in the notes slot. Each candidate declares a region, search, obstacle classes and connector; Layout evaluates the list against one completed surface obstacle set, records the selected candidate and bounded search count, and owns box and connector geometry. The rail, adjacent sides and plot search are configurations of this one model; legacy named rungs normalize to candidates without changing their output. No View field contains concrete coordinates. `layoutMetrics` is the revision-bound metrics/algorithm artifact declared by Render Context, never a renderer font default.

The **kind** of a presentation annotation is the `kind` of the Project annotation its `projectAnnotation` reference selects (an open string such as `risk` or `note`); it is distinct from `purpose`, the closed placement intent. An annotation that carries its own `text` has no kind. Theme kind decoration does not select placement, purpose or text. The explicit View `annotationBindings` contract in Specification44 may bind a Project kind/temporal shape to an ordinary purpose and facet/endpoint; its purpose policy may come from Layout `viewDefaults.annotationPlacement`. No implicit Theme-driven placement or second source of Project narrative is introduced. A Project annotation whose target the View draws is drawn through a binding or a Layout notes slot, or named in `W_PRESENTATION_ANNOTATION_NOT_DRAWN` (annotation id, kind, target and target shape) when neither draws it (#1870). A View with `visibility.annotations` `none` omits annotations by choice and emits no such warning.

For a plot `tail` candidate, the same View intent may complete as a direct
integrated balloon tail or a strict routed connection to a short balloon tip.
Layout records the topology; View does not declare path coordinates. See
[the C3 correction](../design/issue-466-c3-routed-tail-correction-2026-09-29.md).

### 9.2 The View as the connector, and the design it takes from the Layout profile (#1341)

A View is the thin connector between a project and a design. What names the project's ids, fields, dates or wording stays in the
View: `surface`, `selection`, `ordering`, the window's `mode`, `start` and `end`, the grouping key and order, the lane keys, the
comparison bindings (`baseline`, `scenario`, `actual`, `observationSelection`), periods, figures, markers' `source`, headings and
captions, table column captions and sources, annotation anchors and text, hierarchy column, icon encodings. How the surface looks
and is laid out is design, and a Layout profile may supply it as `viewDefaults`, a View body fragment (Specification 33).

Only defaults applicable to the selected surface participate in that overlay.
For `dependency-network`, ingress omits timeline-only defaults (`axis`,
`shading`, `backgroundDecoration`, `timePresentation`,
`annotationPresentation`, and `annotationPlacement`); it does not inject them
and then report them as authored View errors. Explicitly declared forbidden
View members still fail at their View pointers. Compatible defaults retain
the ordinary precedence below; timeline-only defaults retain their ordinary
`table-timeline` behavior.
Ingress retains exact whole-member and split-member default origins. A
semantic failure inside an inherited default identifies the selected Layout
and its `/viewDefaults/...` pointer; it does not blame an authored View member.
Explicit authored values retain their View pointers. Genuine inherited
dependencies (such as named figures or group-header requirements) remain
validated, not silently removed to make a different surface render.

Slice 1 moves these members: `visibility`, `axis`, `deadlines`, `shading`, `timePresentation`, `annotationPresentation`,
`backgroundDecoration`, `progressFill` (whole members), and the design halves of `comparison` (`baselineMarks`,
`missingActualScope`, `deltaUnit`, `facets`), `rows` (`mode`, `trackAllocation`, `packing`, `laneTable`, `points`, `items`) and
`window` (`marginDays`). The rule is whole-member replacement: a member the View declares replaces the design's whole member, a
member it omits takes the design's. The three split members merge one level
down: an omitted member is created from the profile's design sub-members,
while declared sub-members win. Connection fields are never supplied by the
design. Explicitly malformed View members are not repaired; missing required
connection fields remain ordinary View validation errors. The
merge happens at ingress, before validation, so the merged View is validated as the View it is; a Layout profile without
`viewDefaults`, or a View declaring every member, is untouched, which keeps every existing View byte-identical.

**Slice 2 presentation closure (#1341).** `viewDefaults.heading` supplies the
ordinary heading grammar, including default wording templates and `dateForm`.
An explicitly declared View heading replaces it as a whole. The split members
`grouping` and `colorEncoding` follow the same one-level rule as the existing
splits: only `grouping.presentation`, `header`, `tint`, and
`colorEncoding.scale`, `target` may be supplied. A declared header or tint
replaces that nested object whole; grouping keys and color source/domain never
come from those defaults. Project-specific wording and field selections remain
View declarations even when a shared presentation grammar can express them.
An omitted `grouping.tint` takes the design default only for value-bearing
grouping (`field`, `objectType`, or a declared `fieldRole`). It is inapplicable
to `none`, `hierarchy`, or absent grouping, on either surface. An explicitly
authored unusable tint remains an error at `/body/grouping/tint`; ingress does
not remove or repair it.

`viewDefaults.columnStyles` is a named map of column presentation fragments:
`format`, `missing`, `missingBy`, `affixes`, `zero`, `textRole`, `align`,
`headerOrientation`, `width`, `endDisplay` and `text`. A View column keeps `id`
and `source`, and may name `style`. Without an explicit style, it takes a
declared style named after the source discriminator: a scalar source's spelling
or an object source's tagged key (`field`, `comparisonFacet`, `facet`,
`scenario` in the current grammar). This lookup applies uniformly to every
admitted source kind, only if the profile declares that named style. An
absent implicit style is a no-op; an unknown explicit style produces
`E_VIEW_COLUMN_STYLE_UNKNOWN` at `/body/tableColumns/<index>/style`, never a
fallback to another style. Explicit column presentation properties replace the
style's corresponding property whole, including nested objects. Styles never
supply a caption, source or project-dependent matching rule.

Ingress closes styles before validating/parsing the effective View. Existing
required column properties and semantic constraints still apply; incomplete
styles do not create implicit runtime defaults or repair malformed declarations.
Style names are connection declarations, not completed geometry or new resource
identities. Old resources without these defaults retain their behavior. The
remaining marker/period/visual and profile-binding slices are not implied by
this presentation closure.

**Array-entry presentation closure (#1341).** Three optional profile defaults
complete the design/connection split without copying mixed View arrays:
`markerPresentation` supplies `kind`, `label`, `placement` and `date` to each
declared marker; `periodLabelPresentation` supplies `placement` and `overflow`
to each declared period's label object; `visualPresentation` is a map keyed by
the live visual target kind, supplying `ref`, `side` and `decorative` to each
declared visual of that kind. These use the existing property grammars. Defaults
contain no marker source, period identity, visual selector, encoding or project
wording. Generic design voice remains allowed. Period overflow is presentation,
like the existing column endpoint-display and text-wrapping policies.

These defaults neither add nor reorder array entries. An omitted marker array,
an unlabeled selected period, or an omitted visual remains omitted/undrawn.
A label object `{}` may take placement from the design; `{source: actual}` may
take marker form/label from it; a visual with only its target may take a direct
reference. Missing design properties are intentionally closed before validation,
not mistaken for already-invalid input. Explicit properties replace the default
property whole; explicitly wrong-type entries or nested objects are not repaired.
An encoded visual never takes a default direct `ref`, though it may take default
side/decorative intent. Required connection fields and all ordinary effective
View validation remain unchanged. Scene and adapters never see this overlay.

Draft preset preflight applies this same overlay to its declared View/Layout
pair before per-resource contract validation (#1563), even for members later
overridden by explicit inputs. Path/read/header preflight precedes that
declaration-order validation; raw resource identities and unsupported-version
preset provenance are retained. The selected resources are closed again after
overrides. A thin View without compatible defaults remains invalid.

### 9.3 Profile data bindings and wording (#1341, #1344)

A Summary Profile may declare a typed metric `source: {slot: <name>}`.
These are data slots, not Layout nodes. The selected Summary Profile's slot
names form the binding namespace; repeated consumers may share a slot.
There is no `Layout.viewDefaults.slots` member or new resource kind.

The View may supply `bindings: {<name>: <binding>}`. A binding is either
`{object: <Project object id>, facet: planned}` or
`{figure: <figure declaration without id>}`. Figure bindings use the existing
`figures` grammar and Core fact resolution; their figure identity is the slot
name. Existing figure identity rules apply, and collision with an explicit
View figure is an error at the binding. Semantic findings retain the original
`/body/bindings/<escaped-name>/figure/...` pointer, not a synthetic array index.
Binding figure specs are typed at View admission so existing figure consumers
and format checks can read those identities. The use-case boundary separately
checks that each binding name is declared by the selected Summary Profile.
Aliases are not a hidden Summary-only namespace; ordinary consumer scope
restrictions still apply.

A binding to an undeclared slot is `E_VIEW_BINDING_UNKNOWN` at
`/body/bindings/<escaped-name>`. A declared but unbound slot omits its metric
and emits `W_SUMMARY_SLOT_UNBOUND`; a panel with no remaining metrics is also
omitted. No fact or target is inferred from the project. A supplied nonexistent
object is `E_FIGURE_OBJECT_UNKNOWN`; invalid figure facts retain their existing
errors. A valid object excluded by selection retains the existing unavailable
data behavior. Subtree scope requires a planned-object binding; figure scope
and formatting constraints remain unchanged. Admission permits subtree on a
slot declaration and defers that check until its binding is known; it does not
relax the existing subtree rule for any other source form. Separately, the
approved #1344 omission also applies to an undeclared legacy Summary figure
source, with `I_SUMMARY_FIGURE_UNBOUND` (Specification46). Neither exception
changes missing-figure errors for heading or Theme templates.

The View may supply `wording.legend: {<role>: <text>}` and
`wording.summary: {<panel-id>.<metric-id>: <text>}`. A summary key
`<panel-id>.title` overrides that panel's title (#1478). These override the selected
profile's legend label, metric caption or panel title, not its identity, order, source,
format or arrangement. A legend key addresses all entries with that role.
Summary keys address the exact joined identifiers, without splitting on dots;
if multiple metric or panel-title targets have that joined key, an override is ambiguous.
An unknown or ambiguous key is `E_VIEW_WORDING_UNKNOWN` or
`E_VIEW_WORDING_AMBIGUOUS` at its original View pointer. An omitted override
retains the profile label. No panels or arbitrary semantic entries are
synthesized. The bounded realized Actual variants and positive-progress key
in Specification 28 are explicit exceptions, like the Forecast key in §8:
`progressFill` addresses its label, while `actual-ahead`, `actual-on-track`,
and `actual-behind` address qualifier fragments appended to the authored
Actual label. These are wording targets, not new paint or registry roles.

**Built-in wording keys (#1724).** Built-in text (table headers, the as-of marker,
legend labels, the Forecast, Progress, Actual-qualifier and Critical dependency keys, the default lane-table headers, absent-value words) is
looked up by a closed key in the bundled wording table of
[Axis Name Tables](63-axis-name-tables.md#built-in-wording-tables), one complete
table per supported locale (`en-US`, `ja-JP`), selected by the Render Context locale
only. A preset, View or Detail Profile references an entry as `{wording: <key>}` in
`tableColumns[].header`, `markers[].label`, a Detail legend `label` and the
field-grouping `grouping.missing` label (#1865: `grouping.unassigned`, `grouping.other`); each also
accepts a literal. The text of one built-in label resolves, lowest to highest:
(1) the table entry for the locale; (2) a literal authored in the preset (never
translated); (3) the View `wording.keys: {<key>: <text>}` override of that key;
(4) `wording.legend.<role>` or `wording.summary.<id>`, which wins over
`wording.keys["legend.<role>"]` when both address one label. A legend entry of role
`R` is keyed `legend.R`, so `wording.keys` also replaces a literal legend label of
that role. An unknown `wording.keys` key is `E_VIEW_WORDING_UNKNOWN` at
`/body/wording/keys/<key>`. The default `Critical dependency` text of the network
`critical-edge` key is the table entry `legend.critical-edge`; `wording.legend.critical-edge`
(level 4) is unchanged. The closed-day legend role `calendar-closed` is keyed
`legend.calendar-closed` (`Non-working day`, `休業日`), never `Weekend`, because the role also
draws public holidays. A key never changes paint, identity or order, and an omitted
`header` leaves the column `id` as the header.

Before table measurement, omit comparison-dependent columns whose closed
source is absent (#1679). Actual/progress/missing-Actual sources require a
supplied Actual Set; a supplied but empty set retains the column and its
declared missing-value policy. Ordinary finish delta requires Actual, not
Snapshot alone. An explicit forecast fact instead supplies forecast delta
against its already resolved primary/Snapshot baseline. Snapshot and scenario
columns require their corresponding bound source. Use the selected source
contract, never a scan for blank cells or inferred dates. This omission does
not relax required-source, unknown-reference or malformed-fact errors, and
does not mutate the authored View or comparison inputs.

The use-case boundary closes profile connections before fact resolution and
text measurement, preserving authored resource identities in provenance.
Without a selected Summary Profile, Summary bindings and Summary wording are
dormant: their generated aliases do not resolve, while explicit `figures` remain
eager. Active-profile name checks remain strict. `{project: lastPlannedFinish}`
reads the maximum selected Primary/combined planned span end or point at, once
per object identity, excluding ghosts/scenarios; even a group-scoped consumer
uses the whole selected Project, not the current group.
An active Summary figure binding with unavailable as-of or selected finish
omits its consumers with `W_SUMMARY_SLOT_UNAVAILABLE`, naming the slot. A missing
origin explains that an Actual Set with `asOf` supplies it; there is no implicit
clock. Unknown/malformed references and explicit View figures remain fatal.
If all Summary metrics are omitted, Layout receives typed semantic absence
and removes its slot and exclusively empty ancestor frames (Spec33).
Layout still owns completed geometry; Scene and adapters receive resolved
content only. Existing explicit sources and labels remain supported; absent
bindings or wording do not change their output, except the approved unbound
Summary figure behavior specified in Specification46.

### 9.4 Design purity audit (#1341)

The design-purity tool audits Theme, Layout and presentation profiles against
the actual Project referenced by each context. View and Context connections
are excluded. It reports matched Project identifiers and authored wording
with resource pointers using complete-token/phrase comparison rather than
arbitrary substring matching. Resource-root `/version`, `/kind` and `/id`
are excluded: they identify the format and resource, not Project content.
Identifier candidates are limited to Project-reference or user-facing wording
values; a design token or paint name is not a leak merely because a Project
object has the same identifier (#1479). Authored wording phrases remain
lexical candidates. Generic placeholders are
allowed; literal Project wording around them is not hidden. Lexical collisions
require review and do not by themselves prove project dependence or purity.
Strict mode rejects unresolved findings; report-only mode preserves findings
without failing for them. Reference/identity failures still fail the audit.
The tool is evidence, not a replacement for cross-project rendering and the
literal issue acceptance. Existing corpus migration remains reviewer-owned.

Run `python -m tools.check_design_purity --project project.yaml --resource theme.yaml`
for explicit inputs, or `python -m tools.check_design_purity --examples-root examples --report-only`
for every manifest's own Project. JSON output keeps findings qualified by
Project/Context, pointers and match class; summary counts describe findings,
not a count of certified pure resources. Exit0 means a complete audit (and,
without report-only, no unresolved findings); exit1 means findings in strict
mode, and exit2 means an input/reference error. Conformance's
`design-purity-report` is deliberately reporting, not corpus-purity acceptance.

## 10. Diagnostics

View evaluation SHOULD report stable diagnostics for unknown Project, Snapshot, Actual, or object references; incompatible temporal domains; duplicate comparison identity; and invalid explicit windows. Exact identifiers and schema are deferred to the View schema and Application Architecture work.

## 11. Out of Scope

This document does not own the YAML resource envelope, reference normalization, colors,
typography, line styles, scene primitives or coordinates, SVG/tldraw adaptation, or
resource leveling. Snapshot capture and annotation mutation are Command Model concerns;
Automatic Actual-driven changes to the authored plan and DateTime scheduling
remain out of scope. Explicit forecast presentation is defined in §8.5.

## 12. Boundary to Subsequent Documents

`07-style-and-theme.md` may assume that a View Projection exposes selected objects, comparisons, lanes, order, temporal window, and annotation intent. It MUST NOT redefine selection or comparison semantics.

`08-scene-and-rendering.md` may transform a styled View Projection into scene primitives. It MUST NOT become the source of object identity, temporal truth, or comparison alignment.

## 13. Review row composition

View v0.2 may compose several Review Items into one visible Review row. This is View
arrangement intent, not Project containment: each item names one Primary, Snapshot, or
Actual source and one stable Project-local object ID. A row supplies its View-local
identity, label, group, member order, and table subject; Layout and Scene retain all
geometry. The complete contract, diagnostics, and Scene boundary are specified by
[Review Row Composition](38-review-row-composition.md). No View field may use titles,
absolute coordinates, colors, fonts, or renderer identifiers to resolve a row member.
