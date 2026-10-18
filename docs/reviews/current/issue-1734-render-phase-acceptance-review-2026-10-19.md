<!-- chrona:literal-acceptance/v1 -->

# Large-plan render phase attribution

## Literal issue acceptance

### Issue #1734

- Source: [Issue #1734](https://github.com/tya5/chrona/issues/1734)
- Observed: 2026-10-19

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A phase table for 240 tasks (and for 400 if run) on one machine, with how it was measured. | met | Exclusive240 and400 tables below; [240 control ledger](assets-1734/profile.json), [400 candidate ledger](assets-1734/s1-candidate400-profile.json), exact methods and caveats. | — |
| 2 | A recommendation, or a documented stop, if no phase offers a worthwhile intervention. | met | Recommendation below follows the [measured phase costs](assets-1734/profile.json): investigate member-label probes before choosing an algorithm change; use existing explicit hints for the measured edit case. No unmeasured speedup claim or product change. | — |
| 3 | These are pure speed changes, so SVG and Scene stay byte-identical on the 50 public slides and on b240. | not met | Six240 outputs match complete control bytes; [candidate plan/evidence](https://github.com/tya5/chrona/issues/1734#issuecomment-6253883958). Final published disposition and official50-slide snapshot remain pending. | — |
| 4 | Measure end-to-end on 240 and once on 400 after each change, on the same machine. | not met | Member240/400 measurements below are complete. [Graph candidate plan](https://github.com/tya5/chrona/issues/1734#issuecomment-6254199502) requires separate same-base controls/candidate240/400; currently pending. | — |
| 5 | Keep a change only if its end-to-end gain is worth its added complexity, and say why in the PR. Revert it otherwise; that is the stop condition. | not met | Member candidate reverted publicly at [cd8ac0983](https://github.com/tya5/chrona/commit/cd8ac098358ed4a0ba3072e58b7bba468d4eb096); product tree equals measured ready main. Final graph disposition and PR publication remain pending. | — |
| 6 | Do not touch the algorithm, defaults or acceptance rules here. | met | [Approved scope](https://github.com/tya5/chrona/issues/1734#issuecomment-6253352192); candidate diff only prepares immutable private Layout facts and focused tests; collision checks/order/recovery remain fresh. No graph change proposed. | — |

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

The [reviewer approved pure reuse](https://github.com/tya5/chrona/issues/1734#issuecomment-6253352192),
first member-label preparation, then graph preparation, one change at a time.
The [pre-code plan and whole-architecture review](https://github.com/tya5/chrona/issues/1734#issuecomment-6253433414)
confine reuse to private immutable Layout facts; changing-index collision
checks, candidate order, recovery and safety remain unchanged. No schema,
View, Scene, adapter, project-specific rule or migration is introduced.

Member candidate `bbb25d2e3fbc17ed2837388816e13852a866a2ec`, measured head
`7421b458712e37bad85f8ffc84228f7358796393`, shares row/mark maps and
originally admitted span footprints within one top-level placement call.
Each probe still filters current index membership and performs fresh
collision checks. It was rejected and [reverted publicly](https://github.com/tya5/chrona/commit/cd8ac098358ed4a0ba3072e58b7bba468d4eb096).
The reverted tree is identical to ready main `ee4f85938`; the original18
focused obstruction tests pass. No experimental optimizer reached main.
Control `c30a2d58db114394e42688520972f8528c26a2f2` and candidate have the
same relevant resources, Python and non-editable package versions.

### Member candidate: end-to-end evidence

Four serial uninstrumented240 runs, control/candidate/candidate/control:

| Run | Wall seconds | User CPU seconds | Raw stdout / stderr |
| --- | ---: | ---: | --- |
| Control1 | 59.36 | 43.06 | [receipt](assets-1734/s1-control240.stdout) / [time](assets-1734/s1-control240.stderr) |
| Candidate1 | 76.65 | 43.44 | [receipt](assets-1734/s1-candidate240.stdout) / [time](assets-1734/s1-candidate240.stderr) |
| Candidate2 | 59.05 | 42.31 | [receipt](assets-1734/s1-candidate240-repeat.stdout) / [time](assets-1734/s1-candidate240-repeat.stderr) |
| Control2 | 52.35 | 42.59 | [receipt](assets-1734/s1-control240-repeat.stdout) / [time](assets-1734/s1-control240-repeat.stderr) |

All return CLI `status: ok`; full SVG/Scene hashes equal the original control
above. CPU results overlap and wall variability dominates: no defensible
end-to-end gain. Scoped [control](assets-1734/s1-control240-profile.json) and
[candidate](assets-1734/s1-candidate240-profile.json) ledgers, using
[probe v2](assets-1734/profile_render_phases_v2.py), explain why:
baseline-pass span conversion falls from50,160 calls/0.365484s to240
calls/0.005946s, not a saving of the whole14.85s label category.
Both instrumented outputs also match the complete control SVG/Scene bytes.
The actual remaining cost is full candidate placement/collision work, not
the prepared maps alone. No collision verdict is cached.

The public400 input is [`trial-7/big/big.yaml`](https://github.com/tya5/chrona/blob/3f234372863763efdf5d22a140d44da11355f610/trial-7/big/big.yaml),
SHA256 `b892b08c30c638edc8327fb26c76151dd10c41e613ee3e2599faa54e829062db`:
400 tasks,10 groups,578 relations. Its successful uninstrumented control
takes1589.33 wall/954.33 user CPU seconds
([receipt](assets-1734/b400-baseline.stdout), [time](assets-1734/b400-baseline.stderr)).
Candidate400 completed successfully in1223.92 wall/941.73 user CPU seconds
with external time and v2 attribution in the same run
([receipt](assets-1734/s1-candidate400-profile.stdout),
[time](assets-1734/s1-candidate400-profile.stderr)). The
instrumented/uninstrumented pair cannot establish a causal speedup; wall time
differs substantially while CPU is close. Together with repeated240 results,
it does not establish an end-to-end gain worth extra prepared state/plumbing.
Reject and revert rather than retain speculative complexity. Complete400
SVG/Scene bytes also equal the control:
`1f0e7ef4be727eedeae139fbc8e00ee5773f8ee5c1441576fb882f9563ba3787` /
`4feadfafdd03ba8b12f185f5685e0217a91c977704c4e68f1d1f10ba8fb4b7a9`.

### Disjoint400 candidate phase ledger (seconds)

This is experimental7421 source, not an accepted optimizer or an
uninstrumented control phase table. Graph includes v2 envelope conversion;
member placement includes preparation/span conversion. All rows are exclusive.

| Owner/category | Baseline pass | Recovery pass |
| --- | ---: | ---: |
| Graph: envelopes / visibility / sparse / reverse bounds | 82.260690 | 696.587330 |
| Candidate completion | 0.052091 | 0.288587 |
| Candidate validation | 0.395682 | 0.446912 |
| Candidate ranking | 0.003280 | 0.001405 |
| Selection remainder | 5.930851 | 331.287133 |
| Resolution/attempt remainder | 0.034510 | 0.251193 |
| Member-label placement/probes | 52.523219 | 36.227656 |
| Relation-label placement | 0.000105 | 0.000043 |
| Route composition/trial remainder | 0.845093 | 1.582459 |
| Pass subtotal | 142.045522 | 1066.672717 |

Outside passes: member work0.002146s and unwrapped CLI/projection/other
14.190982s; total1222.911366s inside CLI. Stage attempts are normal578/578,
label-visuals2/18, text2/18, marks2/4. Recovery1066.672717s already includes
its graph and selection rows: never add these twice. Unlike240,400 repeatedly
enters fallback stages; the raw ledger retains each stage separately.

### Graph reuse: measured duplicate and bounded candidate

`SurfaceObstacleIndex.route_memo_scope` already keys pure graph results by
exact selected content; `route_visibility_scope` retains selected-port and
obstacle-change identity. `_build_visibility_base` reuses endpoint-independent
visibility, and bounded projection-line caches retain exact facts. The
remaining `_build_sparse_graph` overlays depend on start/end points and
`_reverse_bounds` on their adjacency and target. A wider cache needs proven
identical inputs/hits, not just a shared routing pass.

The control v2 ledger attributes only0.017979s to envelope conversion, not a
worthwhile target. The [v3 identity/admission probe](assets-1734/profile_render_phases_v3.py)
on clean c30 instead records144 builds/84 distinct exact geometry identities:
60 identities occur in both bound modes, no same-mode duplicates or skipped
unknown closures. All144 stores refuse4,012,742 records at the existing4096
capacity ([raw identity ledger](assets-1734/s2-control240-identities.json),
[receipt](assets-1734/s2-control240-identities.stdout),
[time](assets-1734/s2-control240-identities.stderr)). Full SVG/Scene bytes
still match the240 control. Existing cache presence did not prove effective
reuse; the preliminary stopping recommendation is withdrawn.

[Pre-code design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1734#issuecomment-6254199502)
and [Spec50 publication](https://github.com/tya5/chrona/commit/e7ba1a147873fc70f05643fe071afcad2d8b0c3e)
allow one geometry-only slot per prepared selection, across all visibility
bases, keyed by exact endpoints/bounds/grid/selected exemptions. A per-base
cache was rejected because its aggregate size could grow with endpoint pairs.
New content starts empty; previous visibility generations carry no endpoint
geometry; equal-content copies may share immutable geometry. Retained4096
memo capacity and mode-specific keys remain unchanged. Reverse completion,
frontiers, quotas, route validation and candidate order remain mode-correct.

Current candidate owners are only `obstacles.py` and `route_search.py`, with
synthetic graph-memo tests. Fresh ready3277619d0 controls account for the B
integration before candidate measurements. End-to-end240/400, byte gates and
keep/discard are pending; do not equate saved graph builds with speedup.
No algorithms, bounds, defaults or acceptance rules change. Hints stay opt-in.

## Programme-level criteria (optional)

Member measurements/disposition are complete; graph identity/admission evidence,
final graph disposition, official public snapshot and exact-main release
remain pending. No experimental optimizer has reached main.
