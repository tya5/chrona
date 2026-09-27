# Post-geometry feasibility probe (#467, #494)

**Status:** read-only feasibility evidence; not a design decision, implementation review, or acceptance record.
**Published code bases:** the recompletion plan names `33a1ddc0ff750da2ad2a3d0b274658914614af2c` as its published `main` baseline. The fetched `origin/main` in this work session is `b7447aad739185c0a8a7dd865d0a99053b57500d`; its merge base with the WIP is `087feca0e0c3985ab60b243d3b42871234f10c56`.
**WIP under examination:** remote `origin/wip/issue-467-lane-rows`, commit `0a035c640626c3d8d4a85dacc39d7b5284e86bde` (`WIP: fix lane label/mark overlap geometry (#467)`), parent `be7d19de6c19c283efcb2c6bc1a0ed40943a2517`. This commit is unmerged and is not release evidence. It uses a View schema version already present on published `main`; do not merge it as-is.
**Plan:** [lane feasibility and route evidence recompletion plan](../../planning/active/issue-467-494-lane-feasibility-recompletion-design-plan-2026-09-27.md).

## Findings

The committed `02-programme-board` Scene at the WIP commit contains 13 lanes for its 26 items:

| Group | Lane membership |
| --- | --- |
| ait | integration, vibration, tvac; emc, psr |
| bus | pdr, eps; structure, avionics, cdr; bus-test |
| ground | mcs, comms-test, rehearsals; station |
| launch | launch-contract, shipment, campaign, frr; launch |
| ops | leop; first-light |
| payload | optics, detector, payload-delivery; payload-tvac |

The thirteenth lane is the singleton `bus-test` lane. Its planned bar collides with the CDR point in the `structure, avionics, cdr` lane. In the published WIP Scene, the bus-test planned mark spans x=1018.86–1074.67, and CDR is at x=1045.75. This is mark-to-mark occupancy; label placement is not the only reason that the chain cannot be packed under the original schedule.

The scheduler probe selected by the user is a date correction, not an overlap-policy exception. At `avionics-bustest` lag `3wd`, bus-test starts April 30 and still overlaps avionics' actual finish on April 30. At `4wd`, its planned interval is May 3–May 17. The probe changed only bus-test placement and its reported float (41 to 39); integration stayed unchanged. This is a scheduler result, not by itself proof of lane feasibility.

An in-memory WIP rerender at `4wd` produced 13 lanes. The intended chain was together in `lane:bus:structure` (`structure, avionics, bus-test`), while CDR became the singleton `lane:bus:cdr`; `lane:bus:pdr` remained `pdr, eps`. Thus `4wd` satisfies the chain condition in this WIP render but does not meet the ≤12 lane condition.

The geometry explains why the current pdr/eps lane cannot simply absorb CDR using its current label ladder. PDR's row-1 label occupies x=799.58–981.91. EPS's row-1 candidate overlaps PDR; its row-2 candidate is right-aligned to its mark end at x=935.13 and, at width 215.775, starts at x=719.36, outside the plot's x=783.64 left edge. The next feasible choice is inline at x=935.13–1150.91, which covers CDR's point at x=1045.75. CDR's 149.745px label would fit row 1 at x=1050.75–1200.50 if its mark could enter that lane.

As a non-product geometry experiment, an in-memory allocator monkeypatch added a third stagger row above the mark, aligned to the mark start. Combined with the `4wd` relation mutation, this yielded 10 lanes and kept `structure → avionics → bus-test` together. Bus membership became `pdr, eps, cdr` and `structure, avionics, bus-test`. EPS's row-3 label occupied x=867.36–1083.13, allowing its label to clear CDR's mark and row-1 label. The affected bus lane extent was 148.5px: 10px mark + six 21.75px label-row reservations + 8px row padding. AIT and launch also compacted into one lane each, explaining the reduction from 13 to 10.

That row-3 experiment emitted route suppressions for `avionics-cdr`, `station-comms`, and `launch-leop`. The route audit traced all three suppressions to route-quality rejection: all 16/16 candidates were rejected for each relation, with no egress-collision rejection. This does not establish that a third row is an acceptable design. It shows only that this geometry candidate can meet the lane count and chain constraints while surfacing route work that must be resolved.

No label suppression was observed in the row-3 experiment. The rendered canvas grew naturally to 1920×1299.5. The enlarged lane extent and the three route suppressions are material consequences; no acceptance claim is made for the resulting view or adapters.

## Reproduction notes

All probes were read-only and isolated in detached worktree `/tmp/chrona-467-lane-probe` at the WIP commit above. No repository resource, source, generated artifact, remote branch, issue, or board was changed by these probes.

For the WIP lane attribution, parse `examples/halcyon-1/generated/02-programme-board.scene.json`; enumerate `surfaces[0].rows`, and associate each row ID with primitives whose ID begins `member-label:lane:`. Read planned mark and member-label bounds by `sourceRef` to inspect mark and label footprints.

For the scheduler mutation, resolve the ordinary `programme-board` context through `copy_context_closure`, `resolve_render_context`, `LocalSnapshotReader`, and `ReferenceScheduler`. In memory only, thaw `closure.project.scheduler_input`, set the relation with ID `avionics-bustest` to lag `4wd`, reconstruct the `ProjectContract` with `dataclasses.replace(..., scheduler_input=FrozenDict(...))`, replace that closure resource, then call the normal `render_review(RenderRequest(...))` and serialize its Scene. The rerun returned 13 rows and the lane memberships reported above.

For the geometry variant, before that same render call, patch `chrona.presentation.layout.lane_allocation` in memory: add `label-row-3` between `label-row-2` and inline choices in `LADDER`; map it to a distinct label obstacle class; return an `ObstacleRect` from mark start to `mark.left + label_width` in the vertical band `[-3*label_row_height, -2*label_row_height]`; and update the lane's `label_rows_used` to at least 3 when that placement is accepted. The resulting 10-row Scene and its diagnostics are the evidence summarized above. This monkeypatch is a prototype description, not approved product code.

## Disposition

The date correction is the chosen direction for the schedule probe. The `4wd` result alone does not satisfy the lane limit. The generic third-row-start experiment identifies a possible placement-domain expansion, but route-quality failures and the required architecture/specification review remain unresolved. Treat both results as inputs to design work; do not treat either as final design, implementation acceptance, or issue closure evidence.
