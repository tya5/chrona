# Issue 1426 — declared routing policy

## Baseline and design plan

Published base: READY `133332e2833ede4423e775c1dec789db91c2d5cb`.
Authority: [issue 1426](https://github.com/tya5/chrona/issues/1426), including
its revised scope and algorithm review; Specification 50 and the Layout schema.
Stage: design planning; selected design and implementation plan are not final.

Verified: `select_relation_route` ranks all pairs when given a rank callback;
the search uses a finite per-pair quota and path-history state. Label recovery
is conditional, not an unconditional second pass. Layout owns these decisions;
Scene and adapters must receive completed routes, not choose policy.
Published timing evidence is approximately 3,170 CPU-seconds for 1000/228;
new-policy timings and output changes remain unverified.

Baseline focused validation: 69 tests pass in 2.31 s (visibility preparation,
graph memo, path-history/intersection equivalence, routing placement, label
recovery and diagnostic details), in this worktree's Python 3.13 venv.

Use case: authors choose inexpensive deterministic routing or the existing
ranked routing, without a project-size threshold. The default change is an
intentional migration, coordinated with reviewer-owned target declarations.
No developer changes to `examples/**` or managed artifacts are permitted.

### Decisions to close before implementation

- Define exact port-pair order and finite straight/L/Z/U shape order, including
  ties, row-gap/channel derivation, and existing terminal acceptance.
- Define expansion accounting across pairs and label recovery, exhaustion
  diagnostics, zero/invalid budgets, and counters without claiming that a
  bounded search proves geometric impossibility.
- Preserve `best` candidate/quota/order semantics. Cheaper heuristics and
  node/direction dominance require equivalence evidence: different visited
  histories can have different self-overlap-safe continuations. The proposed
  disposition is pending the reviewer response on the issue.
- Reconcile Specifications 50/56, normalization, placement identity and
  diagnostic ownership. Locate actual hot-path costs rather than assuming
  every algorithm-review observation still describes current code.
- Agree a schema-ready preparatory boundary or joint publication so reviewer
  `search: best` declarations precede the default flip. Coordinate with 1427's
  later `unroutable: suppress` declaration without implementing its modes here.

### Whole-architecture findings

- Specification 33 retains required lane labels before routes and one optional
  lost-name recovery. Specification 50 also retains up to three lane-reservation
  routing rehearsals. Merely skipping `surface_route_label_plan` recovery does
  **not** satisfy the new one-pass contract. The selected first-fit phase order
  must bypass lane rehearsals and place lane member names/deltas after routes,
  while retaining already completed axis/period/other required text as obstacles.
  Keep both legacy label/rehearsal rules under `best`; update both specifications
  together before code. Data-only lane membership, label association/reach and
  window admission must not change.
- Specification 33 defines top-level `relationRouting` replacement in derived
  profiles. Preserve that rule; do not merge individual routing members or
  silently inherit a discarded base policy. Existing schema-required limits
  remain required when the object is authored.
- Specification 50 already preserves exact endpoint-independent base visibility
  and incremental obstacle additions (#1420); current tests prove ordered graph
  and reverse-heuristic equality. This is existing shared preparation, not a new
  unimplemented capability. Endpoint graph assembly and reverse Dijkstra remain
  distinct costs. No runtime typing-protocol checks were found in the inspected
  search/routing/obstacle modules; do not claim removing nonexistent work.
- Specifications 37/49 preserve completed Layout geometry and immutable semantic
  inputs; neither Scene nor a usecase should own the new shape/port policy.
  Specification 56 governs optional in-place schema additions and truthful
  ingress failures. Specification 66 transports producer-owned diagnostic facts.
- Shape success must reuse full corridor/terminal preparation and final safety,
  bounds and quality validation, not only a raw segment collision check. Existing
  node-sharing diagnostics remain necessary when first-fit stops before ranking.
  Budget exhaustion remains a search disposition, never a no-safe-route proof.

### Design and evidence order

1. Characterize existing ranked routing, policy normalization and conditional
   label recovery; complete the selected normative design and whole-architecture
   review. Owners: Layout engine/model, routing/search, surface routes and label
   plan; schema/vocabulary/default gates and Specification 50.
2. Publish the implementation plan with independent schema/migration and
   policy/efficiency boundaries, affected files and focused acceptance tests.
3. Implement only approved contracts; batch disposable public materialization,
   route deltas and the three trial measurements. Retain synthetic PR-path
   tests for every corpus rule. Use CI for the full three-OS release gate.

## Literal acceptance (all currently not met for the new policy)

| Criterion copied from the issue | Required evidence |
| --- | --- |
| Under `best`, every existing example and route test is byte-identical. The reviewer declares `best` on the five approved design targets before the default changes; land that YAML first or in the same release. | Legacy-versus-best characterization, batch artifact diff and coordinated reviewer publication. |
| Under `first-fit`, list changed routes per example slide with counts: routes changed, bends ± and length ±. The reviewer accepts or rejects them in the PR. | Per-slide route delta table and explicit PR review. |
| A counter test shows that under `first-fit` a relation settled by a shape performs no graph build. | Synthetic counter test with a graph-building negative control. |
| The three trial inputs are re-measured, and the 1000/228 CPU time is reported against the 60 s budget. | Reproducible CPU/RSS measurements for verified inputs, without substituting wall time. |
| Output is byte-identical across two runs. | Scene/SVG hashes for repeat runs under the declared policy. |
| Do not edit `examples/**`; the reviewer adds `search: best` to the targets. | Authored diff and reviewer-owned migration evidence. |
