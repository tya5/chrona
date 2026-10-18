# Issue 1701 — hierarchy work record

## Published baseline and literal acceptance

Main `381cf404a`; row1 candidate `c0e78982c`, review `73192c558`, on
`wip/issue-1703-1701-display-followups`, integrated with independently reviewed
legend code as `163ba8725`. Row1 is focused-tested, not released. The
[issue record](https://github.com/tya5/chrona/issues/1701#issuecomment-6246724848)
owns its fast-path plan; the [acceptance review](../../reviews/current/issue-1701-hierarchy-acceptance-review-2026-10-18.md)
keeps the full issue open. This record plans **row2 only; no row2 code yet**.
The joint display-followup publication follows the902 predecessors and retains
both literal reviews and full gates; integrated focused tests64 pass.

1. Synthetic: a group with a child gate after its last span shows a range ending on the gate date.
2. Design record for nested grouping (levels, header depth, folding, how presets declare it), reviewed before code; then a synthetic 3-level twin rendered by the bundled presets with no level lost.

Authority: [issue1701](https://github.com/tya5/chrona/issues/1701), Spec06 §6,
Spec38 [row composition](../../specification/38-review-row-composition.md), and
the existing View/Theme/Layout contracts. Trial6 `531f5007e` is reproduction
evidence, not a project-specific core policy. The reviewer requests row1 first.

## Design plan

- **Use cases:** imported three-level containment with/without field-role
  bindings; authored hierarchy/field/object-type/no-group Views; ordinary/lane
  rows; horizontal headers, vertical tags and table-less plot labels; explicit
  selection, comparison tracks, rollups and folded points.
- **Verified:** Core retains parent/depth/path. Explicit hierarchy expansion
  and unbound-role `fallback: hierarchy` are different contracts; the latter
  currently retains only rootmost group identity. Current headers are flat;
  their writing mode is not a declaration of nested-depth support. Existing
  `path` table sources and hierarchy columns must be evaluated before adding
  a new topology or capability mechanism. Lane schema restrictions matter.
- **D1 — capability/closure inventory:** classify every public bundled preset,
  not only the failing fallback presets. Identify how each preserves every
  level and where its declared row/group/label strategy cannot do so. Resolve
  how the all-presets acceptance treats intentionally ungrouped Views; do not
  silently exempt them or change their grouping by inference.
- **D2 — selected contract:** specify visible levels versus depth-limited
  selection; stable group/occurrence identity and order; header-depth support
  versus inner-label-column fallback; folding, rollup and comparison behavior;
  exact authorable preset declarations and missing-capability diagnostics.
  Prefer existing resource mechanisms where they express the rule. Specify
  intentional migrations rather than preserving lossy behavior.
- **Ownership:** Core owns containment/scheduling; View owns selected semantic
  topology and content. Theme/Style describe paint; Layout completes header,
  column, indentation and label geometry; Scene/adapters do not recover paths.
  Review against Specs06/07/08/28/38/49/50/56 and adjacent designs.
- **D3 — architecture review:** check every grouping/row family, source-local
  identities, preset closure, schema/version policy, table measurement, lane
  membership and diagnostics. Coordinate shared projection seams with B's
  #1700; do not absorb its retained-gate/one-summary-mark/guide requirements.
- **Evidence:** synthetic three-level twins through all bundled presets,
  Scene **and native adapter** level/name evidence, counts and affected visual
  outputs inspected as a batch; selection/folding/comparison negative cases.
  Exact public-materializer deltas and full CI remain release conditions.
- **Publication:** publish this plan; then complete the selected design,
  normative specification changes and architecture review; then publish the
  implementation slices/files/tests/acceptance/publication boundaries here.
  Only afterward implement row2. No implementation plan or design-completion
  claim is made by this planning publication.

## Capability inventory

The public library has15 effective closures:7 lane and8 automatic. Layout
`viewDefaults` contribute grouping/header declarations; raw View YAML alone is
not the closure. All use table-timeline surfaces.

| Presets | Rows | Grouping / current label route |
| --- | --- | --- |
| mission-light, control-room-dark, print-mono, executive-light, elevated-light | lanes | responsible-role groups; only executive-light falls back to hierarchy; plot titles |
| editorial, technical-print | lanes | no grouping; plot titles |
| marquee, sunday, target-b, titlecard, yuya | automatic | responsible-role groups with hierarchy fallback; Task title/Phase columns; Yuya uses vertical tags |
| muted-executive | automatic | responsible-role groups with hierarchy fallback; Task title/Owner columns |
| wallboard-dark | automatic | no grouping; Task title/Owner columns |
| chrona-default-draft | automatic | explicit hierarchy, depth all, rollup header; Task hierarchy column |

Existing `tableColumnSource: path` displays full ancestor-title breadcrumbs.
However, lane schema forbids `tableColumns`, `hierarchyColumn` and explicit
hierarchy grouping; its separate lane-table columns have their own contract.
Therefore an ordinary path column alone cannot satisfy all-presets acceptance.
The selected name-source contract below covers lanes, intentionally ungrouped
Views and bound field-role grouping, not only unbound-role fallback.

## Row2 design and architecture review

[Reviewer answer6247026872](https://github.com/tya5/chrona/issues/1701#issuecomment-6247026872)
approves per-member path labels in lanes; ordinary tables retain a literal
path column. Omit ancestor levels already displayed by the enclosing header
or lane, by source identity rather than matching title strings. Keep the
existing separator/fit policy: no new ellipsis rule. All15 presets still need
native three-level PNG evidence with every level readable once. The normative
contract is Spec06 §6.0, Spec38's lane names and Spec50 §3.2.

- Keep grouping keys, selection, ordering, lane packing, folding and rollup
  semantics unchanged. Hierarchy display is independent of presentation groups.
  Current flat/vertical headers are not nested-depth-capable; no new header
  capability framework is proposed.
- Ordinary table closures use existing `source: path`; lane closures use
  one finite `path` member-label component. The default hierarchy closure may
  retain its already lossless depth-all header/Task-column representation.
  All15 effective preset closures must declare a lossless representation,
  including intentionally ungrouped and bound-role designs.
- A path is the ordered source-local ancestor-title breadcrumb including the
  selected item, not a new group identity. Close its text before Layout from
  the occurrence's own Project, including Snapshot/scenario sources. Omitted
  ancestor rows are not invented; names may still appear in the breadcrumb.
  Object IDs provide the label fallback for absent/blank titles; titles are
  never parsed into identities.
- Label admission: `path` is an alternate name source to `title`, alongside
  existing optional `finishDelta`; admit at most one name source, not exactly
  one globally. Existing non-lane `[finishDelta]` stays valid. Lanes require
  a name; omitted content retains existing mode-specific defaults.
  Lane name requirements and `placement: both` name-column checks must admit
  the selected path route: explicit `path` requires/links a path column;
  otherwise keep the current title-column rule, including delta-only content.
  An unrelated path column must not change existing title links. View optional
  admission follows Spec56; evaluate schema equivalence explicitly.
- Share name composition across lane/non-lane/folded label measurement and
  placement; treat path as the existing name component for visibility/style/link
  rules. Table paths and plot paths must use the same source-local text fact.
  Layout still owns measurement, wrapping and overflow; Scene receives completed
  text. Do not hide ancestor loss in elision/suppression without the existing
  pointed fit evidence; the synthetic all-preset gate requires visible names.
- Source audit: primary table paths currently look ancestor titles up in the
  primary Project; Snapshot/scenario factories do not close their own ancestry.
  Close immutable ID/title breadcrumbs at each source factory, then normalize
  display names once for table and plot consumers. Preserve `ReviewItem.title`
  for source diagnostics; do not extend the unrelated federation DTO contract.
- Header coverage is typed and source-local: only an enclosing emitted
  hierarchy object/header covers its ancestor segment. Match object identity,
  not title text, entity IDs, relative depth or a header elsewhere on the slide.
  Preserve unknown/hidden ancestors in the path. Explicit path selection also
  supplies the matching ordinary path column; legacy path columns retain full
  breadcrumbs. This avoids a second path-scope setting.
- **Architecture review — accepted design, implementation not yet started.**
  Specs06/38 keep grouping separate from containment and preserve all existing
  selection/folding/depth contracts. Specs07/28/49 retain Theme/Detail/Style
  ownership and occurrence identity; paths are name content, not new semantic
  roles. Specs08/50 retain Layout measurement/fit/routing and passive Scene/
  adapters. Spec56 permits widening View v0.28 in place; Layout v0.10's existing
  visibility defaults carry the same declaration. Independent source-closure,
  admission and consumer audits agree; root checked the schema and factories.
  No new public diagnostics, header framework or federation contract is needed.
  Preserve old View verdicts and outputs unless path is explicitly selected;
  correcting Snapshot/scenario path ancestry is an intentional source-locality
  repair. Migrate packaged declarations explicitly, never infer from project
  names or change Project dates/data to make the acceptance twin pass.

## Row2 implementation plan

Design publication: `f4475ec01`; reviewer wording approval6247026872.
Implement on a separate row2 branch so the tested legend/row1 release can land
without waiting for all-preset hierarchy evidence. Publish the following
coherent commits in one row2 PR after the joint display followup's ready base.

| Slice | Files / owners | Focused acceptance and evidence |
| --- | --- | --- |
| H1 source/name closure | `model/projection.py`, `model/surface_content.py`, `review/v05_content.py`; a small shared pure name helper if needed | Primary/Snapshot/scenario ID/title segments; exact enclosing-ancestor coverage; no text/entity collision; missing-title fallback; hidden/depth-limited ancestors retained; legacy path output and selected-current links preserved. Test table/plot parity and same IDs with different source titles. |
| H2 authoring and Layout consumers | `schemas/view-v0.28.schema.yaml`, `contracts/resources.py`, label-content normalization; `layout/lane_label_intent.py`, `surface_member_labels.py`, `surface_marks.py`, `key_row_lanes.py` | Admit path and reject title+path; retain delta-only and omitted-content verdicts; matching-source both/link checks. Preflight and final text agree for ordinary, lane, attached, folded and key-row names; existing explicit-window absences and Style identities unchanged. No Scene/adapter hierarchy logic. |
| H3 packaged declarations | Effective View/Layout declarations and source mirrors for all15 preset closures | Explicit name-path choice and ordinary path column except the already-lossless default depth-all route; preserve grouping/packing/rollup. A neutral three-level fixture (also bound-role, no-group and differing-source negatives) proves no intermediate name lost. Render all15 native PNGs as one batch, inspect every level and retain Scene/SVG/source counts. Diagnose rather than silently waive an unreadable level. |
| H4 release review | Existing literal acceptance review; official public-materializer artifact | Schema-equivalence/annotation checks, import-direction and focused presentation tests; official before/after50 SVG/Scene pairs and report diffs inspected as a batch. CI supplies full three-OS pytest/conformance, wheel/smoke, MCP and newest-Python materializer release on the exact main SHA containing both literal acceptance rows. Only then close1701. |

Expected changes are opted-in preset names, their measured text/fit geometry,
and source-local comparison path repairs; do not assert byte identity for
those intentional changes. Unchanged legacy fixtures remain characterization
guards. Do not weaken fit diagnostics or edit example Project data to absorb
side effects. An ownership, schema, visible-selection or diagnostic design gap
returns to this design and its normative specification before more code.
