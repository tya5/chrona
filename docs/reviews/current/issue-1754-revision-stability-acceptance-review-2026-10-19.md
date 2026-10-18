# Issue 1754 — revision stability acceptance

Status: implementation review, **not release accepted**. Product source
`e1d192890`; integrated with ready main
`bd6898017e3314bcfaffa3432d977d9a0f00fdd2`. Current authority:
[work record](../../planning/active/issue-1754-revision-stability-work-record-2026-10-19.md).
Trial inputs are unchanged
[`bf3940dbe9af487ac6cace5458554762594f3477`](https://github.com/tya5/chrona/tree/bf3940dbe9af487ac6cace5458554762594f3477/trial-8).

| # | Literal acceptance criterion | Status and evidence |
| ---: | --- | --- |
| 1 | Synthetic: removing one relation and appending another keeps every other relation's primitive id; hints are accepted for all unchanged relations. | Met locally: `tests/integration/test_revision_relation_identity.py`, both first-fit and best; core identity cases cover anonymous and duplicate relations. CI/release pending. |
| 2 | target-b with `--previous-scene` uses the hints (receipts show accepted hints), or reports why not. | Met in trial CLI receipts: target-b weeks 2/3/4 accept 40/13/40 hints. Nonaccepted instances have invalidated, unusable or absent receipts. No receipt-exposure change was needed. |
| 3 | A synthetic slip that does not touch a relation's endpoints keeps that relation's route; no new through-mark crossing appears where a detour exists. | Met locally: `tests/integration/test_revision_route_corridor.py`, both policies; unchanged endpoint geometry, retained valid corridor, invalidated blocked hint and actual mark-clear replacement path, without relaxed recovery. CI/release pending. |
| 4 | Re-running trial 8 with hints: the changed-primitive count of unchanged objects falls, and the table is posted on the issue. executive-light labels of unchanged tasks do not toggle with the as-of line. | **Not met as a whole.** Weeks 1–4 measured below; week 5 fails with `E_FORECAST_BASELINE_UNAVAILABLE: be-ratelimit`, dependent on [1755](https://github.com/tya5/chrona/issues/1755). Same-candidate raw changes do not fall overall. Label placement excludes only the as-of line, with direct synthetic negative controls; remaining route-driven changes are not claimed resolved. |

## Trial comparison

Per-pair counts, receipt dispositions, exact failures, source/input identities
and reproduction commands are in [the trial summary](assets-1754/trial-summary.json).

Three independent design pipelines; weekly hint chains; one PNG and Scene per
render; identical week-1 output reused. These are same-candidate plain versus
hinted results, not an old-ID normalization presented as improvement. Counts
sum the three available transitions (weeks 1→2, 2→3, 3→4).

| Design | Raw changed primitives, plain → hint | Row-normalized changes, plain → hint | Accepted / invalidated / unusable / absent receipts |
| --- | ---: | ---: | --- |
| executive-light | 189 → 193 | 38 → 33 | 311 / 77 / 118 / 10 |
| target-b | 237 → 237 | 7 → 8 | 93 / 47 / 113 / 5 |
| marquee | 241 → 240 | 11 → 13 | 85 / 51 / 117 / 5 |
| Total | 667 → 670 | 56 → 54 | 489 / 175 / 348 / 20 |

Raw and row-normalized counts are distinct measures; normalization removes
row translations, not route-shape changes. Added/removed primitives and label
toggles are reported separately in the trial summary. No blanket cross-design
stability improvement is established. All six week-5 commands fail; no week-5
PNG/Scene exists. Forecast was not removed to make the batch pass.

Through-mark warning sets are identical between plain and hinted runs in each
available transition; accepted hints do not appear in those sets. Residual
through-mark routes remain, including the Observability-stack crossings. This
is not proof that no detour exists for those routes.

Actual adapter PNGs inspected: executive-light plain week 2 and
[hinted week 3](assets-1754/executive-light-w3.png), target-b plain week 2 and
[hinted week 2](assets-1754/target-b-w2.png),
[marquee hinted week 3](assets-1754/marquee-w3.png). Inventory reservation remains
visible across the as-of line. A remaining `plat-perf` label side change has a
changed dependency route across its old label box; its emitted week-4 label
crosses the as-of line, demonstrating that line is not the suppressor. Aggregate
suppression diagnostics do not prove the blocker for every remaining label.
In target-b week 2→3, accepted `plat-perf--qa-perf` retains its interior
corridor while endpoints translate with inserted rows; endpoint movement still
counts as a raw change. Shape-degenerated and mark-crossing hints are
invalidated. Do not reject safe hint-first corridors merely to improve a count.

## Verification and release gates

Focused batches and architecture checks are recorded in the work record.
After integration with `bd6898017`, focused readable-default/revision tests:
112 passed; two generated-wallboard assertions failed because the checked-in
public Scenes still carry pre-migration indexed identities. They require the
official regenerated snapshot, not a compatibility assertion or a hand-edited
generated file. The newly merged year-boundary test and revision synthetics
passed. PR snapshot/conformance/full shards, affected public-output comparison,
and exact-main three-OS release containing this review remain required.
After the reviewer-1768 integration, required/provisional member-label and
previous-Scene focused tests passed (52 cases).

Schema L1 passed with precise expected Scene deltas. Local L2/L3 had no
semantic mismatch but exceeded the unchanged 60-second timing guard on the
loaded host; CI must establish the isolated gate. No local full pytest was run.

The combined PR also carries reviewer [1768](https://github.com/tya5/chrona/pull/1768),
the independent 1724 wording-key YAML migration and its declared preset-test
normalization. Its English labels are unchanged; source-content hashes change.
It is not a 1754 trial fix, and was integrated after the pinned trial batch.

Ownership review: identity is core-owned, route validation and text geometry
are Layout-owned, completed cone-ground choice travels in Scene, and adapters
do not infer routing, text placement or ground policy. No trial/project data
was changed or preset tuned to pass 1754. No validator, budget or quality limit
was waived.
