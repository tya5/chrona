# Review Row Composition

**Status:** M28 base contract; supplemented by the #467 lane-row design for the lane View version (the next free View version at landing; see the [#467 phase and version correction](../design/issue-467-lane-rows-phase-and-version-correction-2026-09-27.md)).
**Depends on:** Specifications 06, 08, 24, 36, 37 and ADR-0029.
**Owns:** View-local Review row membership and its semantic projection boundary.

## 0. Input closure

M28 uses `chrona/render-context/v0.6` Render Contexts. `body.inputs.snapshot`, when
present, is a typed immutable `snapshot-ref` reference. The resolver reads the
Snapshot resource and then reads its nested immutable Project reference. It schedules
the primary and snapshot Projects independently and requires equal Project IDs before
building Review Items. A closure records each resource's own immutable revision; a
historical Snapshot Project MUST NOT be rejected merely because its revision differs
from the primary Project/configuration revision.

`primary` item sources resolve from the Context's primary Project schedule;
`snapshot` sources resolve from this named Snapshot schedule; and `actual` sources
resolve from the selected Actual set. A View using a source absent from the Context
diagnoses before projection. No source may mean a branch tip, local working file,
implicit latest snapshot, or copied schedule payload.

## 1. Contract

A Review row is a stable View-local presentation composition, not a Project object,
schedule activity, Snapshot record, or Actual observation. It makes one table/timeline
line from ordered Review Items. A Review Item is a View-local instance of exactly one
source placement: `primary`, `snapshot`, or `actual`, aligned by a stable
Project-local object ID. A task, milestone, snapshot placement, and Actual observation
are therefore all ordinary review items; none is a renderer-only exception.

The row model is introduced by `chrona/view/v0.2` View resources:

```yaml
rows:
  mode: explicit
  items:
    - id: fw-qualification
      label: FW qualification
      group: firmware
      tableSubject: snapshot-plan
      items:
        - {id: snapshot-plan, source: {kind: snapshot, object: qualification-task}}
        - {id: current-plan, source: {kind: primary, object: qualification-task}}
        - {id: current-actual, source: {kind: actual, object: qualification-task}}
        - {id: evt-complete, source: {kind: primary, object: evt-complete}}
        - {id: customer-gate, source: {kind: primary, object: customer-gate}}
```

Row `id` and item `id` are View-local and unique. `items` is a non-empty ordered list.
Every item has `source.kind` (`primary`, `snapshot`, or `actual`) and `source.object`.
The same source/object pair may occur more than once only with different item IDs and
only in different rows; an item may not be duplicated in one row. `snapshot` requires
the named Snapshot selected by the View Context, and `actual` requires the selected
Actual observation for that object. `tableSubject` is optional and defaults to the
first item; when present it MUST name one item. `label` is optional and defaults to the
table subject's resolved title. `group` is an optional View-local group key on the row,
never on a Review Item. Items may originate from objects with different semantic
owners/entities and may be reused by several rows; such facts remain Project fields and
do not create a second View grouping authority.

`rows.mode: automatic` has no `items`. It preserves the existing semantic selection,
grouping, and ordering behavior by producing the requested baseline and Actual items
for each selected object in one row. This is
an explicit v0.2 composition mode, not a legacy runtime fallback. In `explicit` mode,
row items are the complete selection and their declared order is authoritative;
`selection`, `grouping`, and `ordering` remain invalid in the View body to prevent two
competing selection/order authorities.

## 2. Projection semantics

The projection contains `ReviewRowProjection` values in row order. Each has
`row_id`, `label`, `group_id`, `table_subject_id`, and ordered `ReviewItemProjection`
values. An item projection contains its View item ID, source kind, stable object ID,
one resolved temporal placement, comparison facts where meaningful, and a deterministic
`member_index`.

Primary and Snapshot item resolution use their named immutable schedule contexts;
Actual resolution remains `Actual.observation.projectObjectId == source.object`. The
same source/object item can therefore appear in each explicitly requested row instance.
Progress remains observed-only and has no scheduling effect. Deltas are derived only
when a row requests both comparable baseline and Actual items for the same object; they
are never inferred from neighboring or titled items.

The table title is the row label. All object-derived table columns use the table
subject's source object; a comparison column uses only an unambiguous matching
baseline/Actual item in the row. A View must choose a different table subject or supply
a later row-specific column mechanism if it needs different values; the Scene never
guesses from a title or mark position.

## 3. Scene, Layout, and accessibility

For M28 automatic and explicit composition, Layout allocates one `SceneRow`
for every row projection, never every item. In `lanes` mode, Layout derives the
lane rows from selected item projections. Row bounds are shared by their item
primitives. Layout assigns items
deterministic completed subtracks within the row; for the original M28 explicit
contract, this was a `member_index` stack, while the versioned collision opt-in
and generated lanes are defined below. Layout owns the measured row height.
An item's primitive ID
incorporates `row_id` and item ID; its `source_ref` remains the stable source/object ID
and its `projection_instance_id` identifies the View row/item instance.

Point milestones and span tasks use their normal mark geometry in their assigned
subtrack. Primary/Snapshot/Actual items use the same source-agnostic item mechanism.
This is not a special milestone-to-task or Actual-to-plan relationship. A later overlay
or progress-indicator policy may deliberately select shared subtracks, but it must be
specified separately and cannot be inferred from source or object type.

Relations and object-anchored annotations resolve against row/item instances. If a
selected source/object occurs once, its instance is unambiguous. If it occurs more than
once, the View annotation must add `rowId` and `itemId`; otherwise composition fails with
`E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS`. Semantic relations whose endpoint has multiple
instances render one connector per unambiguous pair in deterministic row/member order;
no title or nearest-geometry match is permitted.

### 3.1 Data-only generated lanes (#467)

`rows.mode: lanes` is a non-hierarchical table-timeline composition. A lane
contains countable selected Project items; Snapshot, scenario and Actual marks
are facets of their selected item, not additional lane members. Lane membership
is a pure function of the scheduled **planned** dates and selected relation
facts, Project object fields and `attachesTo`, and View selection, grouping,
ordering and `rows` declarations. It MUST NOT read Theme, font metrics,
labels, icons, stroke widths, mark bounds, Actual dates, Scene geometry,
collision obstacles or the output target. The same Project and View therefore
produce identical membership under every Theme and renderer.

View v0.28 adds `rows.packing`, a duplicate-free subsequence of
`[explicit, attached, chain, dates]`, defaulting to
`[explicit, attached]`. The subsequence preserves this order; `chain` and
`dates` are never implicit. `rows.laneKeys` has optional `field` (a Project
object `fields` key) and `byObject` (a map of selected object IDs to keys);
at least one is required when `laneKeys` is present. For an object present
in both, `byObject` wins. The field is ordinary Project domain data; only the View
interprets it as presentation membership. Keys are nonempty strings scoped
to one resolved View group; a key is not a numeric lane index. Unknown
object IDs in the View map, non-string field values and conflicting explicit
keys inside one attached host bundle fail before rendering. Without
`explicit` in `packing`, lane-key declarations have no effect.

If `attached` is selected, a selected point with `attachesTo` and its
selected span host form one atomic countable bundle for membership. The
point remains a distinct member with its own name, mark and count, but
inherits the host's lane; an explicit key on either member applies to the
bundle. A missing or invalid selected host follows #486's validation policy,
never a guessed lane. This attachment is presentation-only and creates no
schedule or dependency edge. If `attached` is not selected, the point is an
independent item.

For packing, a span occupies its scheduled planned half-open interval
`[start, end)`; a point occupies an instant `at`. Two spans with only a
shared endpoint do not overlap. A point at a span's start overlaps it, while
a point at its end only touches it; two points at the same instant overlap.
Only these planned intervals govern `chain` and `dates`. Explicit-key
bundles may overlap in time: their common lane is authored intent, with
Layout resolving their internal mark tracks later.

The allocator first forms attached bundles and explicit-key lanes. It then
visits the remaining bundles in stable planned-start, planned-end, object-ID
and View-item-ID order within each resolved group. For `chain`, a selected
end-to-start relation may continue the successor on a placed predecessor's
lane only if the successor interval does not overlap any independent member
already on that lane. Eligible predecessor ties use relation ID then stable
predecessor identity. For `dates`, the bundle takes the first compatible
same-group lane in stable lane-key order; touching is allowed. A rule that
cannot place a bundle leaves it for the next declared rule; a still-unplaced
bundle opens its own lane. Existing assignments are never relocated.
Group order follows the View; lane IDs derive from group plus explicit key
or stable founding member, never a displayed ordinal. Adding an unrelated
item cannot reorder existing lane IDs relative to one another.

The immutable membership result records each generated lane ID, group,
ordered countable member IDs, rule and source fact that placed each bundle.
It is computed before Theme measurement and passed unchanged to Layout and
Scene. View normalization derives the exact lane-table cell **content** and
count from this result before measurement; no conservative seed-table solve
or geometry-driven membership preflight is needed. Layout measures and places
those cells in one solve, then owns final row height, internal mark tracks,
text/icon bounds, label placement, visible obstacles and routes. If authored
members overlap on one lane, Layout may add internal mark tracks or grow that
lane's block extent but cannot create another lane or change its member IDs.
Within a fixed lane, Layout assigns deterministic first-compatible internal
mark subtracks from completed visible mark facets, including comparison,
Actual, glyph strokes and mark icons; only explicitly declared overlays
within one member or its atomic attached bundle are exempt. Labels are
placed afterwards and do not select subtracks. A Theme or Actual change may
alter subtracks and row height, never
the lane IDs, membership or lane-table counts.
The internal placement unit is a flattened Review projection instance, not
the countable membership item. Layout moves all facets of one instance
together and checks every intersecting facet pair, including pairs inside an
instance. An exemption names the exact two facet IDs; sharing a member ID or
attachment host is not by itself an exemption. For an attached point, Layout
tries the host's subtrack first, but a collision with another attached child
may put that point on another subtrack of the **same lane**. An overlay grants
permission to intersect, not a requirement to share a subtrack. Comparison
instances declared `shared` keep their explicit pairwise overlay relation;
other comparison/Actual instances do not gain one by common object identity.
The `combined` primary instance deliberately composes its planned facet
with its recorded Actual facet (or the missing-Actual marker) in one mark
band; those exact planned↔Actual/missing-Actual facet pairs are declared
overlays. This does not exempt either facet from another instance's marks.
When a `combined` instance selects Actual-sourced progress fill, that fill
also paints over its own planned facet in the same band. Layout declares
only the exact progress↔planned facet pairs for that instance as overlays;
the fill gains no exemption against another instance, attached child, or
unrelated mark. Planned-sourced progress keeps only its own host overlay.
Scene projects completed primitives and serializes the same membership for
a data-only oracle comparison; adapters do not choose lanes. A Scene
footprint cannot approve, reject, merge or split a lane. The previous
pairwise non-redundancy and footprint-concurrency gate is retired.
Layout also completes a typed per-placement lane emission handoff: placement
type and ID, immutable row/member owner, and final visible obstacle facets,
including an explicit ordinal for each part of a multi-part mark. Scene
projects this handoff to its primitive IDs and verifies exact inventory and
obstacle correspondence; it never decodes membership from placement-ID text
or reconstructs visible geometry from Scene bounds. Suppressed text emits no
primitive or obstacle. Decorative non-member paint has no lane owner. A
missing, duplicated or mismatched emitted lane primitive fails closed. This
handoff is absent for automatic and explicit rows and changes no adapter
schema. See the [B3 correction](../design/issue-467-b3-typed-lane-scene-handoff-correction-2026-09-27.md).
The public Scene lane-obstacle class inventory includes `mark` and
`required-label`. A member name is associated with its exact mark through
`hostPlacementId`, not a lane leader facet. The shared Layout obstacle class
`leader-route` remains available to unrelated annotation routing; it is not a
Scene lane-obstacle class. The short-lived Scene v0.6/v0.7 lane enum value is
retired atomically with the #554 member-leader code and public Scene migration.
For lane mode, View-selected comparison facets also close the Layout mark
inventory: an unselected `missingActual` facet creates neither a Layout mark
nor a preflight obstacle, Scene primitive, or lane handoff entry. Scene does
not make a second visibility decision. Non-lane output remains unchanged.

An explicit-window omission retains selected membership and the original
expected source-mark inventory. Layout accounts for it with the typed absence
closure in Spec 50; Scene projects that account under Spec 46 §7.1. This is
not an exemption for an unaccounted missing mark or a geometry-driven lane edit.

Every packed item has a plot-name request; the lane table has no item row to
carry it. The sole temporal exception is an explicit-window omission of its
host: Spec 50 requires a typed, non-spatial label absence instead of a request
with an invented anchor. Membership and the table remain unchanged, and the
source-keyed member suppression count includes that absence exactly once.
Window-admitted names share the normalized component intent in Spec 50 across
preflight and final placement. A lane-mode `visibility.labels` object MUST select plot placement
and `title`; omitted `content` means `[title, finishDelta]`, while a declared
list may omit `finishDelta`. Omitted `side` means `auto`, and an authored
`side` and `visibility.fallback.labels` order (including `inside`) are honored.
With no declared fallback, `auto` tries end, start and the bounded
side-neighborhood stagger; an explicit side tries that side and its bounded
neighborhood. A declared fallback supplies its finite candidate order after
the preferred side. `inside` may exempt only its own host mark, not a
comparison sibling or another item. Every lane ladder terminates in
suppression: if no legal candidate fits, Layout records the source, increments
the surface count and emits no name; it never changes lane membership. With
`rowDistribution: fill`, preflight and final placement share one normalized
member-label intent and Theme-measured box. Preflight uses the completed scale
and selected lane mark/subtrack obstacles; inline-feasible end/start intervals
determine concurrent finite stagger levels and each row's minimum before
surplus distribution; relevant mark-obstacle intervals also contribute to
those levels. Because interval concurrency alone can undercount cross-class
obstructions, the row minimum is at least one measured block level plus
placement clearance per selected lane name above the completed mark subtracks.
This finite conservative envelope does not prescribe final label positions.
The natural requirement may grow the timeline host
when profile constraints permit; a short seed row alone is not grounds for
suppression.

For `fill` lanes, finite measured-box contact search tests the preferred
position and obstacle contacts within one measured stagger step above or below
it, for each declared side. A mark-associated member name must also meet
Spec 50's two-dimensional own-mark distance bound. Rank by side order,
absolute block displacement, smaller block coordinate, and stable identity;
no lattice cap or remote full-row label position is permitted. `pack` lanes
and non-lane labels retain their established bounded side-neighborhood search.

Each suppressed name has a typed Layout fact with lane/member, final row extent,
remaining row capacity and reason `capacity` or `obstruction`, checked against
its suppressed `TextPlacement` and aggregate count. “Cannot grow” means `fill`
has no unallocated timeline block after headers and other row minima. A
capacity reason also requires profile-resolution evidence naming the required
timeline source still short; an extent fallback alone is not evidence. A miss
caused by inline bounds or blockers in the final row is `obstruction`, never capacity. Do not
claim or implement an exhaustive search across hypothetical row heights.
Per-name facts stay in `SurfacePlacement`; a final-row association miss is
`obstruction`. The earlier context 02 zero-suppression output is
characterization; #554's later owner-approved adjacent/start/count rule
supersedes that historical example gate for association failures. An
attached point's required plot label is a distinct exception: View content
normalization reads the active composition (`rows` for automatic rows,
`lane_rows` for generated lanes) and provides its title, planned date and
available point `atDelta` (Spec 06 §8) as one request to Layout. Projection
derives that delta only from matching planned and Actual point endpoints;
Layout measures the completed content request.
After its bounded fit ladder fails, Layout emits that whole label with a
`visible-overflow` outcome and warning rather than silently suppressing facts.
This changes neither lane membership nor Scene's projection-only role.
Omitted
`overflow` means `suppress`; explicit `visible-overflow` is invalid for a lane
name because it contradicts this terminal outcome. These are v0.28 ingress
rules, not silent overrides. Non-lane label policies do not change.
Mark, comparison, icon and text footprints remain relevant to this later
placement and to #494 route avoidance. Required visible labels are obstacles
before routes; a route cannot cross a required lane/member label. The
lane table shows one group/lane summary and optional member count per
generated lane. For `laneTable.label: group`,
the first lane in a group shows that group's title and later lanes have an
empty label. For `laneTable.label: lane`, a singleton shows its selected
member's title; a multi-member lane shows its group's title, with its first
member's title appended when that group has multiple multi-member lanes.
For an ungrouped multi-member lane, the founder member's authored Project
title is its human heading. Generated lane IDs, founder IDs and explicit lane
keys are identity, never display-title fallbacks. A View-requested `Items` column remains declared
intent; public Views with an all-one count SHOULD omit it. This changes
display text, not lane identity or membership (#554). A visible delta table
promise removed during resource migration must be selected in lane-label
content or explicitly retired.
Where a group header already names the group, or grouping is absent, a
counted lane table selects `lane` rather than showing an empty label beside
its count. An unrelated singleton is not automatically a useful lane: a
bundled default may use item-level automatic rows instead.

`automatic` retains its per-object row behavior and exact output bytes, except
for the already declared attached-point fold; `rows.points: own-row` restores
an independent automatic row. In lane mode, omitting `attached` from
`rows.packing` makes the point an independent membership candidate, although
other declared packing rules may still group it.
Authored `explicit` rows and their track policy are separate from generated
lane membership. `rows.laneTable` is required only in lane mode; item-level
`tableColumns` are invalid there. Generated-lane Views declare lane mode
and packing explicitly. A packaged
View seeking transit-map compression must declare `chain` and/or `dates`.
Hierarchical lanes and a `points: key-row` policy are not implied by this
contract. View v0.28 is an intentional schema migration; older View
resources must be migrated explicitly rather than silently reinterpreted.

## 4. Diagnostics and validation

The v0.2 View validator diagnoses empty/duplicate rows, unknown source objects,
unavailable Snapshot/Actual sources, invalid table subjects, `automatic` items,
`explicit` omission of items, and mixed explicit/automatic selection authority.
Projection diagnoses an empty resolved row and ambiguous annotation anchoring.
Layout diagnoses insufficient measured row height. A lane label that cannot
fit is suppressed with source-keyed count evidence, never a membership change.
Committed lane-slide coverage reports visible packed names over all packed
member names from the completed Scene and attributes every suppressed source;
a group heading is not a substitute for a member name.

## 5. Boundary review

| Boundary | M28 decision |
|---|---|
| Project / Schedule | unchanged; items identify existing stable source objects only |
| Snapshot / Actual | unchanged; each is an explicit Review Item source |
| View | selects items/groups, ordered packing rules and lane-key sources |
| Review projection | derives generated membership solely from Project dates/relations and View declarations |
| Layout | owns completed row extent, subtracks, labels/icons, obstacles, ports and routes after membership |
| Scene | projects completed placement to primitive identity and paint order; no geometric search |
| Theme / Color Scheme | roles only; no row-membership policy |
| SVG | serializes completed primitives only |

No deleted Settings/legacy Theme contract, renderer profile, project-ID branch, or
authored coordinate is introduced.
