<!-- chrona:literal-acceptance/v1 -->

# Native content allocation acceptance review (#1214)

Observed: 2026-10-13. Issue remains open. Current developer vehicle:
[PR1463](https://github.com/tya5/chrona/pull/1463), independent numeric source
`49e69a66987b5938a498a89d3d65899d84a11b36`, based on READY45362a34.
[Current design plan](https://github.com/tya5/chrona/issues/1214#issuecomment-6141438610)
and [numeric design/implementation boundary](https://github.com/tya5/chrona/issues/1214#issuecomment-6141643737)
replace the old one-deficit assumption; Spec33 preserves the original least-fit requirement.

## Literal issue acceptance

### Issue #1214

- Source: [Issue #1214](https://github.com/tya5/chrona/issues/1214)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Both synthetic coupled-flow fixtures select200 with native final-manifest verification; global bisection must not skip an earlier fitting branch. | not met | [native fixtures](../../../tests/unit/chrona/presentation/layout/test_coupled_flow_extent.py); Published finite fixtures select200, but content-sized search still returns100; late-wrap and unequal-fr counterexamples remain unresolved. Numeric prerequisites do not complete this row. | — |
| 2 | Fixed/capped/anchored hosts keep requested finite fallback with shortage evidence from the returned manifest; sampled inline capacity is not proof that a growable host is capped. | not met | [counterexample](https://github.com/tya5/chrona/issues/1214#issuecomment-6143294562); Existing capped/anchored controls pass. Unequal-fr native320 fits despite the resolver returning100; a failed probe still causes an unjustified fallback. Precision28 also produces later fitting branches in separately allocated fixed hosts. | — |
| 3 | Candidate-dependent caption/header/axis prefix, natural row/label demand and below-plot reserve use the candidate's completed native inputs, never prior-candidate or fill-expanded geometry. | met | [translation controls](../../../tests/unit/chrona/presentation/layout/test_slot_heading_placement.py); Source49e69a66 completes table/axis/caption local geometry, retains typed prefix_block and reuses each candidate's native measurements. Large-origin tests cover rotated headers, mixed axis geometry and top/header-row/axis-tier captions; candidate-demand integration tests pass. | — |
| 4 | Preserve existing Decimal boundary comparisons, Layout/Scene ownership and finite diagnosed overflow; do not add arbitrary retry caps, duplicate allocators, canvas-only fitting or project-specific branches. | met | [numeric source](https://github.com/tya5/chrona/commit/49e69a66987b5938a498a89d3d65899d84a11b36); Layout owns the correction. Scene/adapters, schemas and authored examples are unchanged; no retry cap, duplicate allocator or additional measurement pass. Existing Decimal context and comparisons remain. Complete search must not claim an ideal affine tail under precision28. | — |
| 5 | Review synthetic fixed/intrinsic/flex/minmax/spanning/nested/flow/aspect and empty/auto/finite cases; batch actual public artifact effects without editing examples to absorb changes; full exact-main release evidence remains required. | not met | [PR1463](https://github.com/tya5/chrona/pull/1463); Numeric focused batches and exact-head CI38383876348 pass; its public artifacts are inspected below. Full search matrix and containing-main three-OS release remain incomplete. | — |

## Programme-level criteria (optional)

None; the numeric prerequisite does not replace literal acceptance.

## Evidence and remaining gate

Focused numeric/heading/axis/Scene batches passed136,121 and73 tests before
the caption-local refinement; the refined caption/native/geometry batch
passed147 and supporting integration/source tests passed51. These are command
results, not a claim of distinct test counts or full release acceptance.
The same measured shape supplies natural demand and translated placement.
A read-only review found no missing currently emitted axis geometry or metadata
translation; deferred grid geometry is completed against the final global plot.

Current numeric-head52636edf snapshot11805185046 from
[38383876348](https://github.com/tya5/chrona/actions/runs/38383876348)
preserves46/46 SVG bytes.42 Scene files change558 numeric fields
only, max delta2.842170943040401e-14; no primitive additions/removals, route,
identity, string or diagnostic-verdict changes. Two reports change: inventory
owner locations and9 contrast coordinate cells; verdicts/ratios/hosts are identical.
Direct tar comparison confirms101 paths,44 changed and no added/retired paths.
The9 contrast cells cross a display rounding boundary (207.513 to207.512);
no ratio, threshold, color, host or classification changes. Exact-head CI passes
all three pytest shards, conformance, MCP, newest reproduction and derived-ready.

Prior run38382286950 failed all three pytest shards:4/3/1 failures, all8 from stale private
fixture Scene bytes; derived-ready failed as their dependent gate.
Conformance, MCP and newest public reproduction passed. There is no independent
failure hidden here. The three private manifest fixtures were regenerated as
one batch:10 Scene files change104 numeric fields (max1.4210854715202004e-14);
all10 SVGs and all structural/non-numeric fields remain identical.
All8 previously failing tests pass locally; upper-tier ordering has121 passing
focused tests. These failures are resolved in successful run38383876348;
exact-main three-OS acceptance remains pending.

[Numeric contract question6143294562](https://github.com/tya5/chrona/issues/1214#issuecomment-6143294562)
records a verified schema-valid native rounding counterexample. Its decision
must precede a complete terminal search proof; do not substitute arbitrary caps,
sampled failure, an ideal real-arithmetic proof or an unresolved-search waiver.
No examples or reviewer board edits. The numeric prerequisite is independently
publishable; complete-search acceptance and issue closure are not claimed.
