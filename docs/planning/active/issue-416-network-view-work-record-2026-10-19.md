# #416 Network View — work record

Status: design plan; no selected contract or implementation approval yet.
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
