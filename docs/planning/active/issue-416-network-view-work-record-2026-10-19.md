# #416 Network View — work record

Status: Design and normative contract approved. `network.member.gap` is an
optional Theme metric beside the existing network metrics; when absent it
falls back to `network.rank.gap`. This supersedes the temporary Layout Profile
proposal in [review 6257221150](https://github.com/tya5/chrona/issues/416#issuecomment-6257221150),
per [reviewer disposition 6267457613](https://github.com/tya5/chrona/issues/416#issuecomment-6267457613).
Implementation `8240e85c0` passes 266 combined focused tests and the unchanged
HALCYON05 materializer. PR/public snapshot and exact-main release are pending.
Implementation baseline: ready `d0dc06f6bc17227cda31cb9df8fbd7dc2dc3077c`.
Authority: [issue and latest scope](https://github.com/tya5/chrona/issues/416#issuecomment-6256891542),
[design approval and spacing correction](https://github.com/tya5/chrona/issues/416#issuecomment-6267457613).

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

The original spacing criterion remains in scope and is met by the independent
Theme metric decision below. Port selection is a consideration, not a literal
acceptance item. No new layout algorithm is authorized.

## Design plan and architecture review

- Reuse the existing selection/filter, field-reference and ordering grammar
  without copying schemas. Keep selection, ordering, edge closure and tie rules
  in their established projection owners.
- Use `nodeLabel.source` with the existing title/id/field-reference forms and
  title fallback for missing/null/unbound values. Preserve containment and the
  existing deadlines/critical-edge rules.
- Member spacing is an independent optional Theme metric beside `network.rank.gap`
  and the two node minima. Its omission resolves to the current rank-gap value,
  preserving prior placement without a resource migration. No Layout Profile
  channel or broader geometry-metric migration is in scope.
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

The plan, approved design and whole-architecture review preceded product code.
Normative behavior is recorded in Specs 06/07/50. This work record is now the
current implementation plan and acceptance evidence map; do not reopen the
resolved metric-owner decision without new evidence. #1754/#806/#1763/#1756
remain separate work and do not change #416's ownership or acceptance scope.

Acceptance evidence must include opted-in selection/labels/order/spacing and
invalid-surface tests, unopted actual SVG/Scene comparison and count table,
focused tests, CI full/reproduction gates and the review-containing exact-main
three-OS release. The implementation plan must map every row above to evidence.

## Selected design and architecture review

Reuse top-level `selection` and `ordering`. A View has one surface, so a second
network selector/order object would duplicate intent, not enable a second
surface. Selection already closes node membership and retains only edges with
both endpoints selected; no invented bridge edges or implicit ancestors.
Projection carries each selected item's ordinal from the existing globally
ordered selection, preserving `direction` and `tieBreak`; Layout groups by
graph rank but does not resolve View ordering again. This replaces the private
network ordering key that lost those two parts of the global contract.
Network projection resolves that global order even when timeline `rows` is
`explicit`: order a selected-node copy through the existing ordering owner,
then project its ordinals. Do not change timeline explicit-row order or let
Project declaration order become an accidental network-order exception.
Selected Project group containment, existing `deadlines` and
`visibility.relations: semantic|critical|none` remain their current contracts.
The deadline producer is `usecases/render_review.py::_network_deadline_projection`;
its placement support is live, not an unfinished feature.

Add optional `body.network.nodeLabel: {source: ...}` to the latest live View
schema without a version bump. `source` is `title`, `id`, or the existing shared
Project field-reference object (`{field}` / `{fieldRole}`). An omitted or null
source uses `title`; an omitted node-label override has the same default.
An unbound node-label role retains the existing per-role
`I_VIEW_FIELD_ROLE_UNBOUND` declaration diagnostic while falling back to title.
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

Rank progression and secondary-axis sibling/container separation (including
the existing leading inset) are independent in both flow directions.
`network.member.gap` is a finite nonnegative Theme distance; zero is explicit,
and absence uses the resolved `network.rank.gap`. This is behavior-preserving
without edits to existing Themes. Keep one metric channel beside the existing
network minima/rank gap; do not add a Layout Profile override or migrate the
other network geometry inputs. No new packing algorithm or port policy.

Architecture disposition: the approved View and Theme metric contracts are
consistent with Specs06/07/09/13/50/56 and #1727. Projection closes selected
label text and ordinal intent; Layout measures that text, resolves the member
gap beside the existing Theme metrics, and closes all geometry; Scene/adapters
remain unchanged. Core/scheduler and authored corpus stay unchanged. Shared
schema references must not be copied. Specs06/07/50 are the normative
authorities; this record maps implementation and acceptance evidence.

Label-field missing/type rules, ordinal order, explicit timeline refusal and
the Theme metric owner are approved. Ports and new algorithms are out of scope.
Normative clauses are recorded in Specs06/07/50. Implementation slices:
(1) View schema/typed contract, pointed timeline refusal, selected label source
and global-order ordinal projection, with schema-equivalence and synthetic
projection tests, including explicit-row Views with descending/tie-break order;
(2) Theme metric admission and Layout member-gap use/default,
with focused Layout tests for both flow directions, zero, explicit spacing and
omission; (3) actual dependency-network SVG/PNG evidence, exact HALCYON05
before/after counts proving unopted output unchanged, literal acceptance
review and exact-main release gates. Expected owners: `schemas/view-v0.28.schema.yaml`
and its equivalence inventory; `src/chrona/presentation/contracts/resources.py`,
`src/chrona/presentation/model/projection.py`, `src/chrona/presentation/layout/dependency_network.py`,
and `src/chrona/presentation/layout/sources.py`; focused tests in
`tests/integration/test_view_v01_schema.py`, projection tests under
`tests/unit/chrona/presentation/model/`, and
`tests/unit/chrona/presentation/layout/test_dependency_network.py`. Add or
adjust a network-render integration test for actual SVG/PNG if current fixtures
do not prove source text and spacing. No corpus YAML is edited to obtain the
unchanged HALCYON05 result. Publish the spec/work-record update before product
code; B1766/1767's shared files have landed on the current baseline.

Current evidence and all six literal rows are in the
[acceptance review](../../reviews/current/issue-416-network-view-acceptance-review-2026-10-20.md).
Publication is batched with independently reviewed 1756 rows 1–2 and the
1754 follow-up in PR1786. Each issue keeps its source commits and literal review;
one combined ready-tip CI/snapshot/release avoids an extra serial landing.
The combined 1754/1756/416 focused batch passes 532 tests, including the two additional
primary-descending ordering cases in `ffb5f6ef4`. This changes publication
granularity only, not either issue's design, ownership or acceptance gates.
No further product slice is planned before PR/official public-output review;
fix any discovered contract gap through design before extending code.
