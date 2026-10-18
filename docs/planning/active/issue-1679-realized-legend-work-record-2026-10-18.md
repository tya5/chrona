# Issue 1679: realized legend work record (2026-10-18)

Status: design complete; implementation planning is next. No product changes.

## Baseline and order

- Published `main`: `d9a10d4ea`, including S2/PR1687 (`5bfa5356b`). PR1689 (#1680) is the active landing; its exact-head CI is running. Inputs: `reviewer/trial-5-inputs` at `9fa6062de`.
- Start product implementation after #1680 integration and publication of the implementation plan. Dev B owns #1682/#1681/#1683 and the next main landing window after1689; do not duplicate its profile/packing changes.
- Design proposal and reviewer approval: [6243827642](https://github.com/tya5/chrona/issues/1679#issuecomment-6243827642), [6243861925](https://github.com/tya5/chrona/issues/1679#issuecomment-6243861925). No further pre-code reviewer approval is required; the PR receives review.

## Literal acceptance criteria

1. A synthetic project with actuals, rendered with executive-light: every distinct realized mark paint has exactly one legend key, and the actual and progress keys use the realized paints.
2. When an encoding replaces the planned paint on every planned mark, no base planned swatch remains; the encoding's entries stand in its place. A mixed case (some planned marks unencoded) keeps the base key.
3. target-b without snapshot or actual has no baseline, actual or in-progress keys and no empty Δ column.
4. A count table of the public example changes, and the PNGs checked.

## Evidence and selected design

- Reproduced the public executive-light command: 13 actual primitives use green `#269D79`, four progress primitives use brown `#8D530F`; the Actual legend key's brown progress inset hides its green ink. The no-comparison target-b PNG retains unavailable keys and a blank delta column. Both PNGs were inspected, not merely Scene counts.
- Normative authorities: [Spec28](../../specification/28-review-detail-profile.md) owns identity, wording/order and bounded derived keys; [Spec60 §4](../../specification/60-declared-colour-scales.md) owns encoded/base coverage; [Spec61](../../specification/61-progress-fill-marks.md) replaces the host inset with a positive-progress key; [Spec06 §9.3](../../specification/06-view-model.md) owns source absence and wording targets; [Spec49](../../specification/49-semantic-presentation-contract.md) defines the shared paint witness/handoff.
- Distinct meanings never collapse because their RGB is equal. Same-class Style variants may have distinct swatches with identical authored wording; this is intentional, not a new colour-label API. Existing authored scale labels remain independent.
- Compatibility impact is intentional: unused/mismatching keys and unavailable comparison columns disappear; actual/progress keys now explain emitted ink. No source YAML or domain data is changed, no new semantic role or schema version is needed. Additive wording targets use the existing open string-key map.

## Whole-architecture review

- **Model/Theme (Specs07/49):** reuse `theme_paint` channels and extract only effective override/gradient admission into a shared typed ink witness. No duplicate Scene resolver, Scene-type import into Layout, or broad paint-framework move. Scene retains bounds-dependent effects and serialization paint assembly. Required capability failures and optional-gradient solid fallback keep existing diagnostics.
- **Layout (Specs28/33/60/61):** reserve all potential Actual paint groups/progress candidates before measurement; final geometry/visibility selects witnesses and one recomposition stays inside those conservative slots, with no routing/reflow loop. The pipeline supplies the same neutral selected-profile capabilities to Layout and Scene. S2 Style scope/scale identity survives; no new selector evaluation in Scene.
- **View/content (Spec06):** normalize source absence when constructing `TableContent`, before measurement. Supplied-empty is not absent; Snapshot alone cannot supply ordinary Actual delta. Existing required-input errors remain errors. No scan for blank cells, domain changes, or defaulting overlap with B1682.
- **Scene/adapters (Spec08):** consume completed entries and shared ink, not domain facts or source declarations to infer legends. Existing finite circle/rule-pair projections remain intentional; pattern/effect geometry is not copied to those shapes.
- Independent Luna audits identified the two genuine gaps (within-class Style wording and paint/capability parity); the rules above close both before implementation. Remaining risk is implementation parity, covered by synthetic and adapter tests, not another owner decision.

## Implementation planning next

Finalize file-owned slices for shared paint parity, source normalization, candidate/witness composition, and final acceptance. Publish that plan before product edits. Required evidence includes synthetic actual/progress/trait/Style variants; equal-ink distinct meanings; all-encoded and mixed planned marks; absent versus supplied-empty sources and explicit forecast delta; focused conformance; one batched public 50-slide count table; and inspected executive-light/target-b PNGs. Full pytest, wheel and reproduction gates run in CI; close only after exact-main release and all four literal rows are verified.
