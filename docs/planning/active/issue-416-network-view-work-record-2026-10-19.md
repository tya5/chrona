# #416 Network View — work record

Status: View selection/labels/order approved in
[review 6257221150](https://github.com/tya5/chrona/issues/416#issuecomment-6257221150).
Spacing belongs in Layout Profile; its existing-input migration boundary is
awaiting [disposition](https://github.com/tya5/chrona/issues/416#issuecomment-6257252824).
No product code yet.
Baseline: published ready `8087e95c59fda483457eefda20a0177d94dbf798`.
Authority: [issue and latest scope](https://github.com/tya5/chrona/issues/416#issuecomment-6256891542).

## Published facts and limits

The current View already selects `surface: dependency-network`; #1727 added
containment, deadlines and critical-edge presentation. The original issue's
claim that a View cannot reach the surface is historical, not today's baseline.
Layout already completes measured nodes, ranks, ports, routes and primitives.
Inspect current projection, schemas, tests and HALCYON slide 05 before selecting
new vocabulary; do not infer absence from the issue's old measurement.

## Literal acceptance

Original issue:

1. A View can select and label network nodes without borrowing the timeline's
   vocabulary by accident.
2. Rank spacing and member spacing are set independently.
3. Member order within a rank is declared rather than incidental.

Latest reviewer scope:

1. A View selects a subset of objects and a label source for the network; a
   synthetic test and a PNG.
2. The same View vocabulary is accepted or refused with a pointed diagnostic
   on the timeline surface where it does not apply, never silently ignored.
3. HALCYON slide 05 is unchanged unless its View opts in (count table).

Original spacing remains an explicit design/review question, not silently
dropped by the newer scope. Port selection is a consideration, not a literal
acceptance item. No new layout algorithm is authorized.

## Design plan and architecture review questions

- Establish which existing selection/filter, field-reference and ordering
  grammar is surface-neutral; reuse its definitions without copying schemas.
- Decide node scope, label source and within-rank ordering, including absence
  defaults, missing values, unknown references, ties and dangling edges after
  selection. Preserve containment and existing deadlines/critical-edge rules.
- Decide whether independent member spacing belongs in this first pass and
  identify its existing metric owner and behavior-preserving default.
- View owns author intent; application/review projection resolves content and
  graph membership; Theme owns paint; Layout alone measures and places nodes,
  ports and routes; Scene/adapters project completed geometry. No Project or
  scheduling semantics may depend on presentation selection.
- Review against Specs 06/07/09/13, network closure specifications, Spec 56
  §3.2/§7, and adjacent #1727 contracts. Optional behavior-preserving schema
  additions stay in place; defaults require runtime behavior, not annotations.
- Define pointed invalid-surface diagnostics, migration effects and extension
  points. Test ordinary synthetic projects, not HALCYON-specific conditions.

## Publication and implementation boundary

Publish this plan before choosing a contract. Next update the living normative
specification and this record with selected design and architecture review;
request reviewer approval before product code. Finalize implementation slices
only then: owned schema/projection/metric files, synthetic tests, SVG/PNG,
schema-equivalence evidence, HALCYON05 counts and release gates. Keep approval
waiting independent of the already-started #1754/#806/#1763/#1756 work.

Acceptance evidence must include opted-in selection/labels/order/spacing and
invalid-surface tests, unopted actual SVG/Scene comparison and count table,
focused tests, CI full/reproduction gates and the review-containing exact-main
three-OS release. The implementation plan must map every row above to evidence.

## Selected design and architecture review

Reuse top-level `selection` and `ordering`. A View has one surface, so a second
network selector/order object would duplicate intent, not enable a second
surface. Selection already closes node membership and retains only edges with
both endpoints selected; no invented bridge edges or implicit ancestors.
Selected Project group containment, existing `deadlines` and
`visibility.relations: semantic|critical|none` remain their current contracts.
The deadline producer is `usecases/render_review.py::_network_deadline_projection`;
its placement support is live, not an unfinished feature.

Add optional `body.network.nodeLabel: {source: ...}` to the latest live View
schema without a version bump. `source` is `title`, `id`, or the existing shared
Project field-reference object (`{field}` / `{fieldRole}`). Absent, use `title`.
The ordinary title is the Project title, not a plot/path label. Field reads use
the existing binding/default resolver: absent, null or unbound role falls back
to that object's title; present strings are used verbatim. A non-string field
fails with `E_VIEW_NETWORK_LABEL_SOURCE`, the source pointer and object subject;
no implicit map/boolean/number formatting or second template language. Empty
strings are explicit empty labels; node minima/ports/relations still apply.
No new paint, font, size or positioning properties belong in this member.

The entire `network` member is refused on table-timeline, including an empty
object, with `E_RESOURCE_SCHEMA` pointing to `/body/network` and explaining that
`surface: dependency-network` is required. This reuses Spec56's structured
schema diagnostic rather than adding a second surface-dispatch error system.
Existing timeline member-label placement/content is not reinterpreted for nodes.

Within each graph-derived rank, consume the already ordered selected items as
ordinal intent. Remove the parallel `_network_order_key` resolver: it currently
loses direction/tie-break behavior. Layout retains rank calculation, containment
and deterministic object-ID ties; ordering changes neither edges nor ranks.
HALCYON05's existing ascending planned-start/id order must remain unchanged.

Put `network.member.gap` in Layout Profile, not Theme, as required by review.
Rank progression and secondary-axis sibling/container separation (including
the existing leading inset) are independent in both flow directions. Values
are finite nonnegative distances, including zero; no new packing algorithm or
port policy. Omission must preserve current placement, not introduce a borrowed
numeric default. Current code actually reads node minima/rank gap from Theme's
`measured_sources.metric_values`; Layout Profile has no network metric block.
The reviewer is deciding whether this slice adds only the new Layout-owned gap
or migrates all existing network geometry inputs and first-party resources.
Do not add an undocumented override/compatibility channel while this is open.

Architecture disposition: the approved View part is consistent with
Specs06/07/09/13/50/56 and #1727. The spacing input boundary above is unresolved.
Projection closes selected label text and ordinal intent; Layout measures that
text, closes both spacings and all geometry; Scene/adapters remain unchanged.
Core/scheduler and authored corpus stay unchanged. Shared schema references
must not be copied. Update Specs06/07/50 before implementation; the issue record
is the review proposal, not a replacement normative authority.

Label-field missing/type rules, ordinal order and explicit timeline refusal
are approved. Ports and new algorithms are out of scope. Finalize slices after
the spacing disposition: (1) schema/typed intent and projection plus tests;
(2) Layout Profile spacing closure plus tests; (3) SVG/PNG, HALCYON05 counts,
literal review and release. Publish normative changes before code. Shared
Specs06, projection.py and render_review.py are currently owned by B1766/1767;
coordinate and wait for those merges before editing them.
