# Issue 254 Advanced-Contract Example Design Correction

**Corrects:**
`docs/reviews/current/issue-254-advanced-contract-example-design-2026-09-22.md`

## Trigger

The first design-conformant feasibility materialization exposed two facts that
the initial resource inspection did not establish:

1. The wallboard table slot cannot place the required four measured columns
   (`wbsCode`, title, total float, Scenario title) and correctly raises
   `E_LAYOUT_TABLE_OVERFLOW`.
2. The proposed integration-to-PSR tree contains no primary critical relation,
   so `relations.mode: critical` correctly emits none. The existing public
   dependency-network evidence identifies the FRR → Launch → LEOP → First
   light chain as critical.

Neither behavior is a defect in Layout or the scheduler. The example's
authored selection was incompatible with the stated acceptance evidence.

## Corrected decision

The sixth slide remains `flight-readiness`, but its small Project subtree is
rooted at `mission-closeout` and has direct children `frr`, `launch`, `leop`,
and `first-light`, in authored order. The root is a `group` rollup. Those
children gain unique WBS labels and declared planned progress; `frr`, rather
than PSR, owns the selected absolute link. This produces the released,
Scheduler-derived critical edges without a presentation override.

The context binds the existing `briefing` Layout Profile, whose table/timeline
allocation can place the four measured minima. It continues to use existing
HALCYON resources and the SVG target; no new layout vocabulary or feasibility
policy is introduced.

The existing `tvac-slip` Scenario remains the automatic baseline. It remains
a Project-owned hypothetical input whose provenance and Scenario title are
visible in the slide, even though this deliberately late critical subtree is
not itself modified by that hypothesis. The focused materializer evidence also
asserts the selected Scenario's closure provenance, preserving proof that the
scenario resolver—not a renderer field—supplied the comparison.

## Revised boundary review

The correction strengthens rather than changes the ownership path:

```text
Project tree/link/progress/scenario -> Scheduler rollup + critical analysis
  -> View hierarchy/critical/scenario selection -> briefing Layout placement
  -> Scene metadata -> generic SVG serialization
```

`briefing` is a pre-existing Layout policy selected by Context; it owns only
the successful measured allocation. The Project does not encode a table width,
and View does not weaken the table overflow rule. The selected chain is based
on Scheduler analysis; Project has no `critical` authoring field and View does
not infer criticality.

## Revised acceptance

The public artifact must contain the three selected critical relation primitives
where applicable to the selected chain, all with `dependency-critical`
semantics; it must contain the FRR title-cell anchor and no row/Scenario anchor;
it must contain hierarchy WBS/float/Scenario cells and selected Scenario
closure provenance. The five prior HALCYON SVGs remain byte-identical.
