# Architecture Review Amendment — L0 Gate Scope (#467, #494)

**Amends:** [lane feasibility and route architecture review](issue-467-494-lane-feasibility-route-architecture-review-2026-09-27.md) after the [L0 gate design amendment](../../design/issue-467-494-l0-gate-design-amendment-2026-09-27.md). **Evidence:** [scheduler-only current-main L0 report](../../research/presentation/issue-467-494-l0-current-main-feasibility-2026-09-27.md). **Implementation sequence:** [plan amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md).

## Review scope and decision

This review checks the amended sequencing against published `main` `68f487a6beaa1c47da430e5b39dd571f7423595f`, Specification 38 §3.1, the #466 route-priority and C3 sequencing corrections, the selected #467 design and its prior architecture reviews, and the #480/#481/#486/#487/#488 contracts. It also checks the active #498 bundled-default design/plan interlock. This is a design/plan review, not lane implementation or issue acceptance.

**Decision:** the amendment fixes a circular evidence gate without changing the chosen lane policy, data correction, route policy, or literal issue acceptance. L0 can establish scheduler facts only. Lane and route acceptance belongs at L3, the first slice that will contain the generic allocator, completed lane geometry, route obstacle inventory, and cause-specific measurements. L3 remains a hard stop: a failed literal criterion returns the work to design before publication of the default/preset migration.

## Whole-architecture consistency

| Concern | Published contract checked | Review result |
|---|---|---|
| L0 executability | View v0.26 schema, `projection.py`, current Layout modules, published automatic-mode Scene | Consistent with the evidence. Schema permits only `automatic`/`explicit`; the current projection has no generated lane-membership path and Layout has no lane allocator. The current Scene therefore cannot prove future lane placement or routing. Treating it as such would misstate the evidence. |
| Schedule ownership | Specification 04; HALCYON Project, Actual, and frozen baseline | L0 may exercise the ordinary scheduler with an in-memory relation copy. L1 owns the current Project lag edit and dependent output batch. Actual and frozen baseline stay unchanged; no data correction is smuggled into the geometry gate. |
| View/Layout/Scene boundary | Specifications 06, 08, 24, 38, 50, 55; #480/#488 | Preserved. View v0.27 expresses mode/label intent. Layout first implements and measures the third-row lane geometry, invokes the shared text-aware row sizing, and completes routes/cause records. Scene projects results; adapters serialize. No lane coordinates or route policy move into the View or adapter. |
| Route phase and obstacles | #466 route-priority correction; Specification 50; ADR-0019 | Preserved. Required lane names remain phase-1 obstacles in the single shared obstacle index; semantic routes retain existing limits. The L0 amendment reports no lane-route result. L3 must measure egress collision, bounded-search failure, and quality rejection separately for every suppression, and maintain the no-crossing invariant. |
| Adjacent composition | #481 group bands; #486 attached points; #487 table columns; #488 containment | Preserved. These remain L3 integration constraints. None supplies a current-main lane engine that could satisfy L0's former requested output. |
| #466 C3 | Published C3 sequencing correction | Correct dependency: C3 follows successful L3 lane output and remains a separate #466 publication. A scheduler-only L0 report cannot satisfy it. If L3 fails or is paused, C3 stays pending and its own design-return conditions still apply. |
| #498 default | Published bundled-default readability design and implementation plan/amendment | L3 must keep the #498 bare bundled-default and initialized-starter evidence gates active if that slice lands before lane migration. Lane default publication must preserve row-guide coverage, label disposition, independent variance labels, perceptibility, Editorial appearance, and byte stability of the named Editorial bundle/gallery slide. A failure is a cross-design stop, not grounds to bypass #498 or weaken either issue. |

## Acceptance and evidence disposition

All six #467 and all three #494 literal acceptance statements remain unchanged. The current L0 evidence reproduces the 2wd/3wd/4wd planned dates and bus-test float, and observes the one-day avionics-actual/bus-test-planned overlap in the current 26-row Scene. It does not prove the ≤12-lane bound, chain placement, label visibility, deterministic lane insertion, preset migration, route-cause accounting, or no-crossing behavior. Those acceptance rows remain open for L3 and the final public artifact review.

L3 evidence must include the exact lane/member inventory for 02 before and after the approved schedule correction and ladder expansion, cause-specific records for every suppressed relation, the named no-crossing test on 02/11/12, diagnostics and Scene primitives, and visible SVG/materializer output. A passing focused test or Scene-only report is insufficient for user-visible criteria.

## Risks and stop conditions

- The 4wd scheduler result establishes the planned date movement only. It does not prove that the three chain items share a lane or that the 02 total stays at or below 12.
- The prior WIP and monkeypatch measurements remain leads, not current-main acceptance. Do not copy their memberships, route candidate counts, or quality labels into L3 evidence without fresh reproduction from the then-published implementation.
- If L3 cannot distinguish egress collision, bounded-search exhaustion, and route-quality rejection per relation without an unreviewed public Scene contract, stop and amend design/specification before proceeding.
- If lane defaults conflict with #498's required bare outputs, #466 C3's post-lane note evidence, or any adjacent ownership rule, pause the relevant migration and publish a reviewed correction. Do not change acceptance criteria in implementation.

**Review disposition:** sequencing correction is architecturally coherent for implementation planning. This review authorizes no product code and declares no lane or route criterion met. Product work may proceed only after this correction and its implementation-plan amendment are published as coherent design records.
