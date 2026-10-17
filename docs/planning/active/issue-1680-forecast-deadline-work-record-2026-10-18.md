# Issue 1680 — forecast deadline

Status: design and architecture review complete; no implementation started.
Implementation waits for Issue419 S2 to merge and the final plan to publish.
Published baseline: main `cd36227548aa349ed1fe3cb261184ef2b73ecd37`.
[Issue](https://github.com/tya5/chrona/issues/1680);
[preceding Style work](issue-419-semantic-resource-work-record-2026-10-17.md).
Keep this record current; Git retains superseded decisions.

## Baseline and literal acceptance

Verified in published code: Core `deadline_statuses` owns the verdict;
`render_review._project_review` supplies original planned placements to both
shown deadlines and warnings, while the projection's primary temporal geometry
can use forecast placements. Layout consumes the completed verdict/finish.
The published main has planned-only semantics in Spec04 §10, Spec06 §7.3/§8.5
and Spec50 §3.4; this branch supplies the explicit normative correction before code.
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

### Selected finish contract (D1)

Select forecast from final View rows and folded members only when the item has
primary/combined source, `temporal_paint` eligibility and a forecast fact.
Actual-only, Snapshot/scenario and context-only header occurrences do not
select a forecast. For each other Project object use its original plan.
Window clipping, zero paint and adapter omission do not change the basis.
Repeated primary occurrences share one object status. Core alone compares
`at`/exclusive `end` in calendar days, in Project order; warnings and shown
deadlines consume that same status. Explicit forecast-render warnings name
forecast/planned and carry `finishBasis`; ordinary no-forecast messages/details and standalone schedule behavior remain
unchanged. Deadline visibility/overrides filter marks, never warnings.

Bounded source/architecture review on S2 `b201711c4` confirms primary fact
ownership, combined/explicit rows and folded-member closure. No second forecast
or date evaluator is needed. Normative authority is Spec04 §10, Spec06
§7.3/§8.5, Spec07 deadline paint and Spec50 §3.4, corrected together here.

### Paint decision (D2) and architecture review

[Reviewer decision](https://github.com/tya5/chrona/issues/1680#issuecomment-6243271356):
retain `deadline-mark`; no estimated colour/dash/role or implicit caption.
Existing forecast delta/legend identifies an estimate. Literal criteria1–3
remain unchanged; the issue's original estimated-paint clause is withdrawn.

Accepted against Specs04/06/07/13/49/50/56 and Scene Specs08/46: Core compares
dates; projection selects source facts; View selects shown deadlines; Theme
owns paint; Layout completes existing geometry/envelopes. Ordinary/folded hosts
reuse one composition; captions receive the selected calendar-day count and
outlines/contrast remain unchanged. Network forecast remains unsupported and
network plan deadlines unchanged. Scene/adapters do not infer basis or compare
dates; no Scene fields, resource identities or schema versions change.
Migration is the intended correction to opt-in forecast runs/warnings only;
no compatibility switch, source-plan mutation or project-specific rule.

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
