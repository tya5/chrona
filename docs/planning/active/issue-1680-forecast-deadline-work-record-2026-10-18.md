# Issue 1680 — forecast deadline

Status: design, architecture review and implementation plan published; I1 implemented
and reviewed (32 focused Core tests pass), not yet integrated or release-accepted.
I2 may run on the published, reviewer-approved S2 source while its test-only CI
repair runs. The single implementation PR still waits for Issue419 S2 to merge.
Published execution baseline: main `e69d4541a2e6829d568a2f5a5ab077aadda499bb`;
Core and its deadline tests are byte-identical to the original planning base `cd3622754`.
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
The literal trial-5 command was independently reproduced with the installed S2
wheel from `b201711c4`: two deadline ticks, zero late runs and zero `W_DEADLINE`.
The two forecast endpoints exceed their deadline tick positions. Baseline inputs:
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

## Implementation plan and publication

Design/architecture publication: `293d0cc52`, before this finalized plan.
Create this worktree's Python venv (`.[dev,render]` and Noto CJK). Core-only I1
may be implemented/tested on the published S1 base while S2 CI/review runs:
it imports no View/Layout/Scene owner and S2 changes no Core file. This is
isolated WIP, not another concurrent code PR. S2's product contract is now
reviewer-approved and its remaining CI repair changes test inputs only. Reconcile
I2 with that published S2 source and implement in parallel; before opening the
single PR, reconcile again with merged S2 and its trusted generated main. This
changes execution order only, not the reviewed design or publication dependency.
No schema/resource migration.

| Commit slice (one atomic implementation PR) | Files and acceptance evidence |
| --- | --- |
| I1 Core status and warnings | `core/deadlines.py`, `tests/unit/chrona/core/test_deadlines.py`: typed `finish_basis`, optional forecast placement overrides and a formatter consuming completed statuses without recomparison. Keep the ordinary warning wrapper. Test point/span, equal/late, per-object fallback/order, explicit forecast/planned warning basis and unchanged ordinary payloads. No projection/Scene edits in this parallel slice. |
| I2 Projection integration | `presentation/model/projection.py`, `usecases/render_review.py`, model/usecase tests: one eligible forecast map from final rows/folded members, one Core status tuple for warnings and `_shown_deadlines`. Cover combined/explicit/actual-only/hidden rollup/repeated/omitted-window cases. Existing `ReviewDeadline.finish` carries geometry; no new Scene or unused paint fields. I1/I2 must not merge separately. |
| I3 Render evidence | New `tests/integration/test_forecast_deadlines.py` plus existing forecast-render, deadline overrides/caption, ordinary/folded and network regression modules. Assert actual SVG/Scene tick/run endpoints, late/kept warnings, unchanged no-forecast bytes and unchanged Theme stroke/outline. No trial-specific product branches. |
| Release gate | Official public materializer batch: no-forecast SVG/Scene count table, inspect intentional/diagnostic report diffs without editing generated paths. Render trial-5 inputs at the pinned evidence ref and inspect both late runs in PNG. CI supplies full pytest/conformance, installed-wheel and three-OS exact-main evidence. |

Publish I1/I2/I3 as coherent commits on the WIP branch, then one PR after S2;
the earlier design and plan commits stay independently reviewable. Write one
short acceptance review with every literal row, exact commit, PR/CI links,
count table and PNG evidence. Publish/release that review before closing1680.
Issue1679 follows; the reviewer board stays untouched. A contract gap returns
here and to the specification, is reviewed/published, then code resumes.
