<!-- chrona:literal-acceptance/v1 -->

# Large-plan render phase attribution

## Literal issue acceptance

### Issue #1734

- Source: [Issue #1734](https://github.com/tya5/chrona/issues/1734)
- Observed: 2026-10-19

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A phase table for 240 tasks (and for 400 if run) on one machine, with how it was measured. | met | Exclusive phase table below; [raw ledger](assets-1734/profile.json), [probe](assets-1734/profile_render_phases.py), raw CLI receipts/timings and environment alongside them. The explicit small-edit cold/hinted comparison is below. No400 run. | — |
| 2 | A recommendation, or a documented stop, if no phase offers a worthwhile intervention. | met | Recommendation below follows the [measured phase costs](assets-1734/profile.json): investigate member-label probes before choosing an algorithm change; use existing explicit hints for the measured edit case. No unmeasured speedup claim or product change. | — |

## Measurement

Measured clean source: `9672b4c85e523e2be10f804f39fe7f0145766c0e`
(ready main, before1715's diagnostic-only change). One Apple M1 machine,
macOS26.3.1/25D771280a, Python3.13.7; dedicated editable venv with
[package versions](assets-1734/environment.txt). Four serial runs on2026-10-19
JST, not simultaneous render jobs. These are single observations, not a SLA
or a statistically established speedup.

Input: [public240-task/336-relation Project](https://github.com/tya5/chrona/blob/3f234372863763efdf5d22a140d44da11355f610/trial-7/big/b240.yaml),
SHA256 `d4a2c834a3cf1cb28adac139c5d887806f6bd88d0465ffd85adec9a2694dd97d`.
The edit changes only `t0-0.title`: `Platform work item 1` →
`Platform work item 9`; IDs, dates and relations are unchanged.

Run from the pinned checkout's own venv. Ordinary command:
`/usr/bin/time -p .venv/bin/python -m chrona render PROJECT --preset chrona-default-draft --progress --output OUTPUT.svg --emit-scene OUTPUT.scene.json`.
Use the unchanged input for baseline, the edited input for cold edit, and add
`--previous-scene baseline.scene.json` for hinted edit. For attribution replace
`-m chrona` with `PROFILE_PROBE --output profile.json --`, retaining the
unchanged input and ordinary arguments. The probe `--self-test` verifies nested
exclusive charging, aliases, return/exception transparency and pass/stage tags.
It refuses dirty/wrong checkouts. Its argv-path digest is not a hash of implicit
resources; the pinned source and installed font package identify those here.
CLI JSON `status: ok`, not process return alone, confirms all four successes.

| Run | External wall seconds | Raw CLI receipt | Raw stderr/time |
| --- | ---: | --- | --- |
| Baseline cold | 53.99 | [baseline](assets-1734/baseline.stdout) | [timing](assets-1734/baseline.stderr) |
| Instrumented unchanged | 50.50 | [profile](assets-1734/profile.stdout) | [timing](assets-1734/profile.stderr) |
| One-title edit, cold | 49.36 | [edit-cold](assets-1734/edit-cold.stdout) | [timing](assets-1734/edit-cold.stderr) |
| Same edit, explicit hints | 38.90 | [edit-hinted](assets-1734/edit-hinted.stdout) | [timing](assets-1734/edit-hinted.stderr) |

Instrumentation covers49.523694s inside the CLI after imports; startup accounts
for the remainder of its external50.50s. The baseline's3.49s higher external time
shows inter-run variability: this pair cannot quantify profiler overhead.
Hints saved10.46s in this observed pair, not a general performance promise.

## Disjoint phase ledger (seconds)

All rows are exclusive, including recursively invoked member-label probes.
Graph and candidate callbacks include shape-first paths, not only fallback
search. Both passes attempted resolution stage `normal`336 times; no other
resolution stage was observed. Trial/pass subtotals must not be added again.

| Owner/category | Baseline pass | Recovery pass |
| --- | ---: | ---: |
| Graph: visibility base / sparse graph / reverse bounds | 10.960710 | 4.873142 |
| Candidate completion (`prepare`) | 0.020732 | 0.104795 |
| Candidate validation (`accept`) | 0.148666 | 0.131052 |
| Candidate ranking | 0.001329 | 0 |
| Selection remainder | 1.140850 | 7.137657 |
| Resolution/attempt remainder | 0.006405 | 0.006307 |
| Member-label placement/probes | 14.852285 | 1.189266 |
| Relation-label placement | 0.000025 | 0.000064 |
| Route composition/trial remainder | 0.318334 | 0.461516 |
| Pass subtotal | 27.449336 | 13.903798 |

Outside those passes: member-label placement0.002464s; unwrapped CLI,
projection and other work8.168096s. Total49.523694s (rounding aside).
Sparse graph calls:129/15; reverse bounds:60/0; visibility base:1/1.
Member-label calls:209/1, plus one outside both passes. Thus recovery costs
13.903798s in total, not that amount plus its graph/label/selection rows.

## Output and hint evidence

Profile/control SVG SHA256:
`e644ae9d546b34472c1f42175bf15eb2866689ff9a38a1bc7c4cb08d909773fb`;
Scene SHA256:
`fbccbf718a1ce241fb0394f9c2e6f550e97a12b477e0baedc84d17b05f8b7928`.
Both complete files are byte-identical, not merely similar counts.

Every run retains1635 primitives and240 member labels. Relative to baseline,
cold edit changes only its table cell and member label (2 existing IDs).
Hinted edit changes those2, another2 member-label positions, and3 dependency
routes (7 existing IDs); neither adds/removes primitives. Aggregate warning
codes/counts are unchanged. Hints are revalidated proposals, not geometry
identity or a protected-feasibility proof.

Two hint summaries correspond to the baseline/recovery routing passes:
accepted316/315, unusable20/20, invalidated0/1, actualSearch8/9, out of336 each.
The672 receipts represent336 unique relation IDs twice:315 accepted in both,
20 unusable in both (`terminal-semantics`), one accepted then invalidated.
Fourteen unique relations searched at least once (17 searched receipts).

## Recommendation and boundary

First investigate the member-label reservation-probe algorithm:209 baseline
calls consume14.85s, while graph preparation consumes15.83s across passes.
`_route_blocked_candidate` re-enters `place_member_labels` for individual
declared candidate rungs. Its per-call context/index preparation is a concrete
structural review target; existing route visibility/graph caches do not cache
label probes. Compare reusing immutable prepared geometry/context with the
current per-candidate work. Do not reuse collision verdicts across changing
obstacle indexes, drop declared candidates, skip recovery or change budgets.
The measured category is an upper bound, not a predicted saving.

Bring that design/cost comparison for review before algorithm code. Reject a
behavior-preserving candidate if it changes selection/safety/output or fails
to improve repeated same-host end-to-end controls; a semantic change instead
requires explicit design approval and disclosed output deltas. Existing
explicit previous-Scene hints already help this one-edit case; do not present
them as a new feature or apply them silently to cold renders. Stop here for
this profiling slice. No400 run: no approved intervention yet warrants its
cost, and240 already distinguishes the dominant owners. Do not extrapolate
the timings to400 or invent a size threshold/speed target.

## Programme-level criteria (optional)

Pending publication and required exact-main release evidence. This report
changes no product algorithm, schema, defaults or layer ownership.
