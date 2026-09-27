# Architecture Review — Lane Feasibility and Route Evidence (#467, #494)

**Reviewed:** [lane feasibility and route correction](../../design/issue-467-494-lane-feasibility-route-correction-2026-09-27.md) against published product behavior at `95d1513c` (later `main` additions through #498 implementation planning are documentation only), Specifications 04, 06, 08, 24, 38, 50, and 55; ADR-0019; the #466 route-priority correction; #467 lane design and phase correction; and the #480/#481/#486/#487/#488 adjacent contracts. **Evidence input:** [read-only feasibility probe](../../research/presentation/issue-467-494-post-geometry-feasibility-2026-09-27.md). This is a design review, not implementation or release acceptance.

## Review findings

| Area | Contract checked | Finding |
|---|---|---|
| Schedule ownership | Spec 04; HALCYON Project, Actual, immutable baseline | Raising the current Project relation lag preserves schedule semantics and recorded actuals. At 3wd the planned start still coincides with avionics' actual finish; 4wd moves it to May 3. Keep the baseline snapshot immutable and regenerate dependent current-plan artifacts. |
| Collision and chain | Spec 38; #467 selected design | The 4wd shift removes temporal mark overlap so predecessor-lane preference can keep the required named chain together. The allocator still rejects geometric conflicts and is deterministic. |
| Label feasibility | Spec 38; #480 Spec 24 row sizing; #488 containment | A third bounded, lane-local label row is a Layout placement choice. Its measured extent must enter the shared row requirement and remain inside the lane. The measured probe indicates this expands the affected lane and allows a ten-lane result, subject to new-main reproduction. |
| Phase order and obstacles | #466 route-priority correction; Spec 50; ADR-0019 | Required lane names remain phase 1 and in the shared obstacle index before semantic routes. The correction does not introduce a second obstacle inventory, route exemption, or optional-label priority inversion. |
| Route failure | Spec 50 §3.3; #494 literal row 1 | Three quality-rejected suppressions are compatible with the explicit acceptance text when each has measured cause and none is egress-collision. Preserve quality thresholds and no-crossing behavior; do not describe the probe as proof that those dependencies are rendered. |
| Adjacent composition | #481 group bands; #486 attached milestones; #487 table allocation | Group-local lanes remain rows within each group's band, attached points continue to follow their host, and lane table sizing uses shared table measurement. No duplicate policy ownership is introduced. |
| Version and layers | Spec 06/08/55; schema inventory | v0.27 is the next version after published v0.26. View declares intent; Layout measures, allocates, routes, and records cause; Scene projects completed geometry; adapters serialize it. No schema addition is needed for the third row. |

## Decision

The correction is architecturally coherent and resolves the measured feasibility gap without weakening literal issue criteria. It supersedes the two-row-only ladder and the earlier proposed narrowing of the chain criterion. It keeps route quality and required-label safety intact. The findings from the unmerged WIP and monkeypatch remain provisional inputs; implementation must be rebuilt from published main and produce public adapter evidence.

## Literal acceptance interpretation

Issue #467's six acceptance items remain unchanged. Its row 1 is a hard ≤12 bound and requires `structure → avionics → bus-test` on one lane; the selected 4wd schedule correction and extended ladder are intended to satisfy both and require current-main measurement. Issue #494's three criteria remain unchanged. Its first row permits remaining suppressions only when all are enumerated with measured causes and none is attributed to egress collision. The probe's three quality rejections are a candidate disposition, not a final acceptance result. The no-crossing test must continue to pass on 02, 11, and 12, and lane membership changes on 02 must be attributed.

## Risks and gates

- The probe was an in-memory geometry mutation on an unmerged WIP branch. It does not verify current live fonts, schema, presets, generated outputs, or adapter rendering.
- A 4wd relation-lag change affects scheduler-derived dates, float, and dependent renderings. Confirm all current contexts and any copies; preserve snapshot immutability and Actual provenance.
- A third row adds lane height and may change canvas extent or later row placement. Inspect the complete SVG/Scene batch, including visible names and delta labels.
- Route-quality suppressions leave semantic relations absent from the slide. Their acceptability is narrowly supported by #494's literal criterion and requires explicit diagnostic evidence for each relation; no claim of complete route coverage is allowed.
- Current public View v0.26 must be the schema migration base. The stale WIP v0.26 and the phase correction's earlier v0.25 expectation are not authority.

**Review disposition:** design approved for implementation planning only. Before product code, publish the normative Specification 38 amendment and implementation-plan amendment. Reproduce the 4wd and third-row results from current main; if the lane limit, chain, route cause, or required-label conditions fail, return to design.
