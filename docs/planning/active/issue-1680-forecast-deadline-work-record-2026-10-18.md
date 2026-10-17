# Issue 1680 — forecast deadline

Status: design plan only. Implementation waits for Issue419 S2 to merge.
Published baseline: main `cd36227548aa349ed1fe3cb261184ef2b73ecd37`.
[Issue](https://github.com/tya5/chrona/issues/1680);
[preceding Style work](issue-419-semantic-resource-work-record-2026-10-17.md).
Keep this record current; Git retains superseded decisions.

## Baseline and literal acceptance

Verified in published code: Core `deadline_statuses` owns the verdict;
`render_review._project_review` supplies original planned placements to both
shown deadlines and warnings, while the projection's primary temporal geometry
can use forecast placements. Layout consumes the completed verdict/finish.
Spec04 §10 and Spec06 §7.3/§8.5 currently retain planned-only deadline semantics;
the issue therefore needs an explicit normative correction, not a Layout fix.
The trial-5 observations are reported evidence, not yet independently reproduced:
[inputs at 9fa6062de](https://github.com/tya5/chrona/tree/9fa6062de/trial-5).

1. A synthetic forecast whose finish passes the deadline draws a run to the forecast finish and emits `W_DEADLINE` naming the forecast. A forecast that keeps the deadline draws only the tick.
2. Without `--forecast`, output is unchanged (count table).
3. The trial-5 command above shows the two late runs in PNG.

The command referred to in criterion3 is:

```sh
chrona render trial-5/plan/current.yaml --actual trial-5/plan/actual.yaml --snapshot trial-5/plan/baseline.yaml --forecast --preset trial-5/looks/tbk/preset.yaml
```

## Design plan

Use cases: late/kept forecast, point `at` and exclusive span `end`, ordinary
and folded hosts, repeated primary occurrences, absent/completed forecast,
hidden deadlines and selected/non-temporal/comparison-only items. Preserve
ordinary scheduling warnings and no-forecast output; do not mutate source plans.

Resolve before code:

- Define which projected primary occurrences select forecast as the comparison
  basis. Geometric clipping or adapter omission must not decide Core policy.
- Specify one per-object effective finish/basis and one Core verdict consumed
  by both the warning and every shown host; decide the fallback for objects
  without an eligible forecast occurrence. Retain Project order and endpoint rules.
- Define warning basis copy/details while retaining no-forecast diagnostics.
- Resolve the requested estimated-run treatment against Spec06 §8.5's existing
  planned-paint plus `*` convention. The [reviewer question](https://github.com/tya5/chrona/issues/1680#issuecomment-6243035188)
  is open; no new role, colour, dash or implicit caption has been selected.
- Review shared network deadlines (forecast remains unsupported there),
  folded packing, outlines, captions, contrast and Theme capability ownership.

Architecture checks: Core compares dates; projection selects source facts;
View selects shown deadlines; Theme owns paint; Layout completes geometry and
ink envelopes; Scene/adapters do not infer basis or recompute lateness. Reuse
the existing deadline composition for ordinary/folded hosts. No project-name
branches, trial-data patches, duplicate evaluator or new scheduling constraint.

## Planned publication and evidence

1. Publish this design plan on a WIP branch; no product changes or new PR.
2. After the open paint decision, complete the selected contract, review it
   against Specs04/06/07/49/50 and publish normative corrections plus the
   finalized implementation plan before code. Reconcile with merged S2 first.
3. One implementation PR: Core verdict/warning and usecase projection together,
   then completed paint/geometry transport and synthetic regressions. Owned
   files: `core/deadlines.py`, `usecases/render_review.py`, projection/deadline
   Layout models and shared deadline owners as required by the selected design.
   No schema/resource migration is assumed; document one if the design needs it.
4. Focused Core, forecast-render/warning, ordinary/folded deadline and network
   regression tests; actual SVG/PNG late/kept proof; no-forecast public count
   table; trial-5 PNG inspection. Batch materializers and generated review.
   CI supplies full pytest/conformance, wheel and three-OS exact-main release.
5. Keep one literal acceptance row per criterion in the release review. Publish
   implementation/review, inspect official artifacts and exact-main release,
   then close1680. Issue1679 follows; the reviewer board stays untouched.

No implementation slice is approved by this plan alone. A discovered contract
gap returns here and to the normative specification before implementation.
