# Review Row Composition

**Status:** M28 base contract; supplemented by #467 lane-row design for View v0.23.
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

### 3.1 Collision-aware lanes (#467)

View v0.23 adds `rows.mode: lanes` for non-hierarchy table-timeline selection.
View supplies selected items, grouping, ordering and required plot-label intent;
Layout composes group-local lane membership from measured mark and required
name/delta footprints. A row is a lane with a stable group/representative
identity, not a Project object or an authored View row. Source/item identity
never depends on lane ordinal. A predecessor lane is preferred only when dates
and measured geometry permit; otherwise deterministic first-fit opens another
lane. A name cannot be suppressed; no fitting candidate opens a new lane or
uses a recorded visible-overflow terminal placement. The left table has
declared group/lane summary and optional count, not one arbitrary member's
facts. Versioned explicit rows may opt into collision allocation while
retaining authored row/member IDs and table subject. The exact contract,
admitted domain and migration are in the [#467 design](../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md).

`automatic` is still the exact per-object row behavior, including its original
table cells, points policy and output. `rows.points: key-row` is not created by
lane mode. Hierarchical rows remain `automatic` or authored `explicit` until a
separate ancestry-preserving lane design exists.

## 4. Diagnostics and validation

The v0.2 View validator diagnoses empty/duplicate rows, unknown source objects,
unavailable Snapshot/Actual sources, invalid table subjects, `automatic` items,
`explicit` omission of items, and mixed explicit/automatic selection authority.
Projection diagnoses an empty resolved row and ambiguous annotation anchoring.
Layout diagnoses insufficient measured row height or an unplaceable required
label before Scene/SVG output, subject to the declared visible-overflow policy.

## 5. Boundary review

| Boundary | M28 decision |
|---|---|
| Project / Schedule | unchanged; items identify existing stable source objects only |
| Snapshot / Actual | unchanged; each is an explicit Review Item source |
| View | owns authored explicit row identity/membership and selected item/group intent; generated lane membership is Layout-owned |
| Layout | owns row/lane assignment, subtrack and label geometry, measured bounds, ports and routes |
| Scene | projects completed placement to primitive identity and paint order; no geometric search |
| Theme / Color Scheme | roles only; no row-membership policy |
| SVG | serializes completed primitives only |

No deleted Settings/legacy Theme contract, renderer profile, project-ID branch, or
authored coordinate is introduced.
