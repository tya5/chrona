<!-- chrona:literal-acceptance/v1 -->

# Native content allocation acceptance review (#1214)

Observed: 2026-10-13. Issue closed after exact-main release38396884738 SUCCESS.
Accepted source: `555916e6ceffcca7d71a4fa767ca2c4d51087a8e` (PR1465).
Base: READY `b8cdf5ad2cd35a86c847fd16f9d04021b89fe6b0`.
[Current work record](https://github.com/tya5/chrona/issues/1214#issuecomment-6141438610).
[Owner scope decision](https://github.com/tya5/chrona/issues/1214#issuecomment-6144755026)
accepts the two original synthetic fixtures selecting200 under local-frame rule B
and unchanged public outputs. General complete-search proof is withdrawn.
Spec33 is the normative authority; the broader rational-migration WIP is excluded.

## Literal issue acceptance

### Issue #1214

- Source: [Issue #1214](https://github.com/tya5/chrona/issues/1214)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Both synthetic coupled-flow fixtures select200 with native final-manifest verification; global bisection must not skip an earlier fitting branch. | met | [Original fixtures](../../../tests/unit/chrona/presentation/layout/test_coupled_flow_extent.py) now exercise both finite and auto modes at minimum100; each returns200, no shortage, and native final capacity100. Coupled search scans ascending only to a verified fitting bound. | General proof withdrawn by owner decision6144755026. |
| 2 | Fixed/capped/anchored hosts keep requested finite fallback with shortage evidence from the returned manifest; sampled inline capacity is not proof that a growable host is capped. | narrowed | [Fixed-host controls](../../../tests/unit/chrona/presentation/layout/test_coupled_flow_extent.py) pass in finite and auto modes with requested100 and timeline80/20 shortage. Failed180 probes in the two original growable fixtures now produce verified240 bounds and first-fit200. Unverified witness failure remains a heuristic fallback, not a global infeasibility claim. | [Owner decision6144755026](https://github.com/tya5/chrona/issues/1214#issuecomment-6144755026) withdrew general-proof requirement; an actual-slide missed branch gets a new issue. |
| 3 | Candidate-dependent caption/header/axis prefix, natural row/label demand and below-plot reserve use the candidate's completed native inputs, never prior-candidate or fill-expanded geometry. | met | [PR1463](https://github.com/tya5/chrona/pull/1463) supplies local table/axis/caption geometry. Each search candidate invokes the existing native solve and its own sizing/demand callbacks; no prior candidate's geometry is reused. | — |
| 4 | Preserve existing Decimal boundary comparisons, Layout/Scene ownership and finite diagnosed overflow; do not add arbitrary retry caps, duplicate allocators, canvas-only fitting or project-specific branches. | met | [Correction](../../../src/chrona/presentation/layout/engine.py) confined to Layout engine; existing Decimal comparison operators and allocator unchanged. Scene, adapters, schemas and authored examples untouched. The scan ends at a verified native fit, not a retry cap. | — |
| 5 | Review synthetic fixed/intrinsic/flex/minmax/spanning/nested/flow/aspect and empty/auto/finite cases; batch actual public artifact effects without editing examples to absorb changes; full exact-main release evidence remains required. | narrowed | [Focused tests](../../../tests/unit/chrona/presentation/layout/test_coupled_flow_extent.py) and supporting engine/content/source/natural geometry/heading/canvas tests113PASS. [Snapshot run38394497838](https://github.com/tya5/chrona/actions/runs/38394497838) preserves all101 declared outputs byte-for-byte; [Exact-main release38396884738](https://github.com/tya5/chrona/actions/runs/38396884738) succeeds on555916e6, including all three OS pytest/conformance/wheel-smoke jobs, MCP and newest public reproduction. | [Owner scope decision6144755026](https://github.com/tya5/chrona/issues/1214#issuecomment-6144755026) withdraws general complete-search matrix proof; exact-main release is still required and cited in the closing comment. |

## Programme-level criteria (optional)

None; scope disposition comes from the linked explicit owner decision.

## Evidence and remaining gate

The minimal correction retains the uncoupled auto and finite branches. A coupled
auto request verifies the native source-deficit candidate even if its demand probe
fails, then scans in ascending integral order to a verified bound. If no tested
bound fits, the existing requested allocation/shortage evidence is retained.
This is explicitly a limited heuristic, not global feasibility proof.

Local-frame rule B is specified in Spec33: cross-host relative geometry is computed
before one origin translation; Decimal boundary comparisons are unchanged.
Focused command: own-worktree Python3.13 venv, pytest on coupled-flow extent,
intent engine, content-flow block allocation, content-resolution diagnostics,
source sizing, surface natural geometry, slot-heading placement, canvas viewport
warnings and surface content-phase integration:113PASS in6.83s. A read-only Luna
review found no actionable layer/regression defect; fixed and aspect-coupled
fixed-block controls retain requested allocation and original shortage evidence.
The merged numeric prerequisite PR1463 passed full release
[38386951262](https://github.com/tya5/chrona/actions/runs/38386951262).
That earlier release is not acceptance for this new correction.

Public batch: final product head3a6597ec, PR1465, snapshot artifact11811621355
from successful run38395134796, against READYb8cdf5ad. Direct tar-member comparison finds
101/101 identical files, including46 SVG and46 Scene JSON files; zero changed,
added or removed paths. CI preview independently reports Changed paths:0.
Final-head CI38395134796 passes all three PR shards, conformance, MCP,
newest reproduction and derived-ready. The earlier five local literal-review
formatting violations were corrected before the successful final-head gate.

Final release: [38396884738](https://github.com/tya5/chrona/actions/runs/38396884738)
completed SUCCESS on exact-main555916e6, which contains the published acceptance
review and scoped implementation. All three OS jobs independently passed
conformance, full pytest and wheel/smoke; MCP floor and newest public materializer
reproduction passed. Owner-authorized scope is complete. No examples or board edits.
This post-closure archive records the completed gate; no product change.
