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

### 3.1 Collision-aware lanes (#467)

The lane View version adds `rows.mode: lanes` for non-hierarchy table-timeline selection. In lane mode, every packed item's name and selected delta is required text: it is measured and reserved by lane allocation, and placed inside its own lane in Layout's first closure phase, before semantic dependencies (Specification 50 phase contract, #466). In other modes item labels remain optional and follow dependencies.
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
admitted domain and migration are in the [#467 design](../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md)
and its [lane feasibility and route correction](../design/issue-467-494-lane-feasibility-route-correction-2026-09-27.md).

The bounded lane-label ladder may use three stagger rows, with start- and
end-aligned candidates in stable order at each row. Layout includes every used
row in the lane's measured block extent and the shared required-row sizing
path. This is a generic Layout policy and does not add a View coordinate or
per-project branch. Project schedule corrections for individual acceptance
cases remain data migrations, not layout policy; historical Actual
observations and immutable baseline schedules are not rewritten to satisfy
layout. The third row is an available candidate, not an acceptance prerequisite
for a particular lane count. No numerical lane-count target is an acceptance
gate. On completed 02 Scene geometry, every same-group lane pair MUST resist
merging in both directions through a measured cross-member visible-footprint
collision, unless an approved enforced chain-separation rule names that pair.
The current predecessor preference is not such a rule. Per-group primary-mark
overlap concurrency is reported beside final lane count as an explanatory
lower bound; full-footprint inline concurrency and concrete collision witnesses
explain any gap. Scene lane-mode primitives MUST retain typed lane-row and
countable-member provenance for this audit without adding placement policy to
Scene. See the [rule-based acceptance correction](../design/issue-467-494-rule-based-lane-acceptance-correction-2026-09-27.md).
For this read-only Scene audit, each lane Scene row carries the completed
absolute block coordinate of its shared mark-band top. The checker aligns
source and target mark-band coordinates in both directions; it MUST NOT infer
the anchor from the row's full bounds, a glyph part, or semantic port-host
bounds. Lane primitives carry typed row and countable-member provenance.
The [Scene anchor correction](../design/issue-467-494-scene-lane-anchor-correction-2026-09-27.md)
defines the lane-only v0.6 schema fields and checker cases.

Required lane names remain obstacles before semantic routing. Routes retain the
declared quality bounds and may be suppressed when no candidate meets them.
Cause-specific evidence for #494 MUST distinguish egress collision from route
quality rejection and bounded-search failure for each suppressed relation; a
quality-rejected route is not reported as rendered. The #494 acceptance allows
non-egress suppressions when every remaining suppression is listed with its
measured cause.

Lane membership and required block size are closed by one Layout-owned
preflight after a finite seed arrangement supplies the table/timeline inline
bounds and before the content-height solve. This preflight is final-block-
coordinate-free, not inline-geometry-free: it measures the selected marks,
comparison/actual/attached-point footprints, required titles and deltas, and
their finite ladder in the seed inline scale. Its immutable plan is the sole
authority for lane identity/order, selected rung and natural row extent.
Content-height resolution and final composition consume that same plan; the
composer MUST NOT reallocate lanes. The final arrangement MUST preserve the
plan's lane-driving inline bounds and scale, or lane mode fails with
`E_LAYOUT_LANE_INLINE_UNSTABLE` before output. This excludes silent coupling
from a block-dependent aspect-ratio constraint. `automatic` and `explicit`
retain their existing path and bytes.

The lane plan's mark geometry is completed in a typed `MarkBandFrame`: its
inline scale, lane-local mark-band origin (zero for lane candidates), height
and role offsets are explicit. One Layout mark-geometry composer serves
automatic/explicit track frames and lane-local frames without changing the
former formulas or conversion order. Preflight retains exact candidate/facet
and required-label closure, selected `as_of`, and measurement, Theme, font and
scale identities. The content-height solve and final composer consume this
immutable lineage. The final composer checks those identities, then translates
completed local geometry exactly once through the final mark-band anchor
carried as `SceneRow.lane_mark_band_block`; it MUST NOT remeasure, reconstruct
the frame, change a rung or reallocate. A changed cutoff or measurement
authority fails before Scene emission. See the [S2b closure correction](../design/issue-467-b1b2-s2b-closure-reconciliation-correction-2026-09-27.md).

The lane table's measured width is reserved before membership from the finite
candidate set: all possible group/representative labels and the maximum
selected-item count bound the `Lane`/optional `Items` columns. The completed
plan supplies exact one-per-lane cells and actual lane row count. The measured
envelope is intentionally conservative; final cells MUST fit it. The timeline
and table block requirement uses the completed lane count and natural lane
heights, never the original per-item row count. Group bands include those
expanded rows and their own headers. See the [L3b preflight correction](../design/issue-467-494-l3b-prelayout-route-evidence-correction-2026-09-27.md).

A selected primary Review row is one atomic lane candidate bundle. Its
comparison/Actual facets contribute geometry without duplicate names or
counts; a point attached under #486 stays on its host candidate's lane but
retains its own required title/date/delta, mark, port and count identity.
Packed member labels are atomic required bundles: measured title/selected
delta text and any resolved leading/trailing `labelVisual` icons move together.
Layout evaluates each finite rung with completed component text/icon geometry,
exact visible footprints and natural block extent; it selects the whole bundle
or a new lane, never text without its icon. The selected lane plan carries the
completed placements to Scene, and both text and icon are phase-one required
label obstacles and source-keyed Scene footprints. Automatic-row icon
coordinates MUST NOT be copied into lanes. See the [label-visual correction](../design/issue-467-b1b2-lane-label-visual-correction-2026-09-27.md).
Semantic relation/annotation ports belong to the completed mark slot, not
necessarily to an emitted primitive part's unexpanded bounds. A source-keyed
owning facet carries separate completed `port_host_bounds`; its ports MUST lie
inside those host bounds, while its primitive commands MUST remain inside
their exact `primitive_bounds`. The first emitted facet of each semantic mark
owns its ports in stable part order; siblings do not duplicate them. Host
bounds are not an added collision footprint and MUST NOT widen primitive
geometry. See the [S2b port-host correction](../design/issue-467-b1b2-s2b-port-host-bounds-correction-2026-09-27.md).
Vector icons retain one source-keyed collision facet per completed path, while
Scene emits one ICON primitive per placed icon. Each path facet carries typed
shared emission-group identity/asset facts and its own completed path order,
paint intent and already-scaled stroke treatment; raster icons retain one
viewport facet and exact payload. B2 validates each group and copies one ICON
without reloading or retransforming assets. The placed viewport is not an
extra path footprint. See the [S2b icon emission correction](../design/issue-467-b1b2-s2b-icon-emission-closure-correction-2026-09-27.md).
Layout admits a bundle only when all member marks and required labels fit;
it cannot place a child later or flatten its name into the host's text.
Each accepted member has a closed expected-emission inventory derived from
selected Review semantics before placement lookup. Required mark variants,
compound parts, grouped icons, progress and label components must each have
one completed projection or an explicitly approved intentional-absence reason;
missing or extra emitted primitives fail before Scene construction. This
inventory, not source-ID parsing or a post-plan Theme lookup, determines
projection cardinality. An attached host resolves to one exact projection
instance; missing or ambiguous hosts fail rather than dropping a child.
Unattached points are independent candidates. The natural lane frame contains
one mark level and up to three stagger text rows above it. The whole frame,
not the mark alone, is centered in the row's padded usable area under `pack`
and `fill`; role-specific marks never stretch with surplus. Automatic and
explicit member-index track placement is unchanged. See the
[candidate-footprint correction](../design/issue-467-l3b-candidate-footprint-correction-2026-09-27.md).

Within a lane bundle, each `LaneMember` represents one countable selected
Review item: the root/host or an attached point. Only these item identities
appear in lane membership, representative/predecessor identity, and optional
lane-table item counts. A same-object comparison or Actual facet contributes
geometry and provenance under its countable member; it is not an additional
lane item, lane-table count, or required name.

Each countable member's Layout mark carries immutable source-keyed facets for
its emitted primitives. Each facet retains a stable primitive identity, Review
projection-instance identity (the View row ID plus item ID, or the stable
projected object instance in automatic mode), facet purpose/source kind, stable
source reference, semantic role and primitive type, completed Layout geometry,
the renderer-neutral visible footprint, and stable source ports tied to that
exact instance where applicable. Thus the same source/object used in two
explicit rows retains distinct facet and port identity. Compound glyph and icon
parts retain individual primitive identity in their one semantic member. Every intentional
within-bundle mark overlay is an explicit facet-identity relation. The
allocator checks every facet footprint; only those declared mark pairs may
overlap. This allowance never applies to required labels, other candidates, or
routes. Completed geometry and its footprint/ports remain associated in one
immutable value so final composition can realize the exact collided geometry
without re-deriving the source facet.
Overlay endpoints must both exist exactly once in the same candidate bundle,
be purpose/type-compatible, and authorize only that pair rather than a
transitive group exemption. Shared comparison tracks, compound mark parts,
declared attached-host parts and progress clipped to its host can qualify;
stacked comparison tracks remain obstacles. Duplicate, missing or invalid
facets and undeclared internal overlap fail before allocation. Source object
ID, View item ID, Review projection instance, countable member ID and emitted
primitive ID remain distinct through this validation.

For B1b-2 mapping, Layout receives the selected Actual cutoff explicitly from
the existing normalized `PresentationContract.time.as_of`. Layout does not
load Actual resources or duplicate this value in `ReviewProjection`. A selected
open Actual (`openUntil: "asOf"`) with no cutoff fails before allocation with
`E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE`; it cannot be assigned a guessed end.
The cutoff used by preflight and final composition must be identical. These
source-keyed facets and cutoff rules are specified in the
[B1b-2 facet/count/cutoff design correction](../design/issue-467-b1b2-facet-count-asof-design-correction-2026-09-27.md).

The B1b-2 candidate mapper closes each mark and selected icon to a
stroke-aware, renderer-neutral visible-extent footprint before allocation.
It uses the same resolved Theme geometry roles, mark variant, seed scale,
normalized icon closure, and icon stroke scale as final composition. It does
not resolve or construct Scene paint. A stroked segment retains its
unexpanded centerline and carries stroke width once in `ObstacleSegment`; a
rectangular footprint carries already expanded bounds in `ObstacleRect`.
Visible stroke extent and collision clearance are separate quantities and
MUST NOT be applied twice. Multi-part glyphs retain their primitive identity
and contribute the union of their part footprints. A raster icon reserves
its placed viewport; a vector icon reserves its transformed control-point
envelope and per-path stroke extent. A clipped progress fill contributes only
its visible clipped extent and its own stroke, if any. Missing geometry,
unsupported commands, or invalid metrics fail before allocation with
`E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE` or the underlying stable Theme
diagnostic; an incomplete mark is never silently omitted.

For a stroked rectangle, the visible envelope expands the emitted bounds by
half its stroke width on each side. For a segment, the obstacle index applies
half the stroke width from its centerline. For a stroked path represented by
a control-point envelope, Layout expands that envelope by ten times the
stroke width on every side. This target-independent conservative bound
accommodates admitted miter limits up to ten without changing adapter output
or introducing a Scene paint policy. It is deliberately loose; the completed
Scene's pairwise non-redundancy audit and required-text/route gates decide
acceptance, not a numeric lane ceiling. A failed rule check returns to design
rather than target-specific allocation. `ScenePaint` does not carry a
miter-limit field, and Layout
MUST NOT invent paint conversion or a miter-limit override. See the
[miter-envelope design amendment](../design/issue-467-l3b-b1b-2-miter-envelope-amendment-2026-09-27.md).

Layout also owns the geometry currently constructed after layout in
`scene/v05_builder.py`: Theme-selected built-in point shapes, Theme glyph
parts, point legend swatches, and transformed normalized vector icon paths.
The completed Layout result carries path coordinates, primitive/part identity
and paint order, and geometry-bearing stroke widths before candidate collision
checks and Scene construction. It preserves the existing contain-center glyph
fit, built-in diamond outline override (ignored for glyphs), `paint: none`
omission, part ordering and IDs, close-point conversion, deterministic float
arithmetic, vector icon cap/join and scaled stroke width, and point legend
variant. Scene projects these completed values without deriving or
transforming path geometry. Theme glyph and icon path paint intents are passed
to `ScenePaintResolver`; Scene MUST NOT modify the completed `ScenePaint`
after resolution. Existing automatic/explicit and material-icon SVG outputs
are byte-characterized across the ownership move before it is accepted.

`automatic` is still the exact per-object row behavior, including its original
table cells, points policy and output. `rows.points: key-row` is not created by
lane mode. Hierarchical rows remain `automatic` or authored `explicit` until a
separate ancestry-preserving lane design exists.

In the lane View contract, `rows.laneTable` is required only when
`rows.mode: lanes` and is invalid for `automatic` and `explicit`. The existing
`tableColumns` grammar declares item-subject columns; it has no group/lane
subject, so lane mode rejects `tableColumns` and uses only its separate finite
group/lane summary. When a migration removes a visible delta table column, it
must preserve that promise by including `finishDelta` in lane-label content.
That migration condition is reviewed against the source View and acceptance
evidence; it is not a universal schema rule for lane Views that make no such
promise.

### 3.1.1 Default policy and packaged preset migration (#467)

The schema requires each View to declare `rows.mode`; it does not infer a mode
from omission or reinterpret an existing immutable View. Product authoring
commands and templates that create a new default View MUST emit
`rows.mode: lanes` when the lane mode is available. A user may explicitly
select `automatic` for one-item-per-row review. This is a producer policy,
not a schema default.

At the #467 L3c migration baseline, every built-in presentation preset View
MUST use `rows.mode: lanes`: the seven entries in
`src/chrona/resources/presets/library.yaml` and the separate selector View
referenced by `src/chrona/resources/presets/default.yaml` (eight Views total).
Each lane View declares its lane table and required title text; it also
declares `finishDelta` when the source preset promised visible item deltas.
Lane mode uses only group/lane summary columns, preserves item identity in
Layout labels, and cannot silently fall back to `automatic`. Hierarchical
composition remains outside this lane contract until an ancestry-preserving
design is accepted. The named `editorial` preset is a lane preset; the
reference-faithful Editorial appearance remains a separately named gallery
entry backed by its own pinned corpus Context and is not a preset rendering
exception.

This adoption list describes the L3c resource migration and does not mean
future catalogue entries may inherit an implicit mode. Every View remains
schema-explicit, and each future default preset must be authored and reviewed
as a lane View or receive a separately approved design correction.

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
