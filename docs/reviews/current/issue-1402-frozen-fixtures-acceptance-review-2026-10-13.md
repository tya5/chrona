# Frozen fixture acceptance (#1402)

Source implementation `0f0ff28e`, based on READY `8ce44cb0`. No authored examples
changes. Public fixture inputs are frozen; runtime-generated evidence is not.

| Literal acceptance | State and evidence |
| --- | --- |
| With `examples/controller-z`, `controller-z-ja`, `aster-ssd` and `attached-milestones` temporarily removed in a local check, the full suite passes. State in the PR that this check was run. | **Not met as originally written; reviewer narrowed the gate** in [6133101699](https://github.com/tya5/chrona/issues/1402#issuecomment-6133101699). Approved isolated check on `de599109`: 10734 passed, 5 failed, 20 standard skips, 580.17s. One retired gallery key fixed with focused evidence; hosted-DVT and annotation-box witnesses are reviewer-owned removal prerequisites. Two packaged gallery declarations still require [disposition](https://github.com/tya5/chrona/issues/1402#issuecomment-6133512564). No full-suite success claim. |
| No test reads those example paths. A grep check in the PR shows it. | Met for retired input reads: frozen-input AST guard covers split paths in all tests and both tools; approved removal run reveals no retired input loads. Documentary inventories are deliberately not input reads. PR includes the search command and findings. |

Focused fixture/AST/reachability/corpus/gallery/ledger tests: 28 passed. Fixture-only
public materializer check: 10 contexts, 20 declared outputs; all 20 equal current
published counterparts. Ten Scene metadata updates, zero SVG changes. All 739
existing schema probe/document verdicts remain unchanged; fixture paths/baselines
were repointed rather than refreshed to change answers.

Isolated removal state was fully restored: dedicated worktree clean; preserved
backup SHA-256 `9388c586b269c30defd335b7516a871a4f2301f14667b98a19708b446a4d7f6c`.
The examples consolidation/catalogue migration remains reviewer-owned. Exact-head
PR CI and final release remain pending; keep the issue open.
