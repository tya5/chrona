# Issue 1701 — hierarchy work record

## Published baseline and literal acceptance

Main `381cf404a`; row1 candidate `c0e78982c`, review `73192c558`, on
`wip/issue-1701-group-range`. Row1 is focused-tested, not released. The
[issue record](https://github.com/tya5/chrona/issues/1701#issuecomment-6246724848)
owns its fast-path plan; the [acceptance review](../../reviews/current/issue-1701-hierarchy-acceptance-review-2026-10-18.md)
keeps the full issue open. This record plans **row2 only; no row2 code yet**.

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
