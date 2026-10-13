# Frozen fixture acceptance (#1402)

Source implementation `0f0ff28e`, based on READY `8ce44cb0`. No authored examples
changes. Public fixture inputs are frozen; runtime-generated evidence is not.
Published in [PR1448](https://github.com/tya5/chrona/pull/1448), public
`87afea92e76feb43d0f478b2a1632391f3026c24`;
[exact-main three-OS release38320123870](https://github.com/tya5/chrona/actions/runs/38320123870)
succeeded. Preview11777977260 has zero changed public paths.

| Literal acceptance | State and evidence |
| --- | --- |
| With `examples/controller-z`, `controller-z-ja`, `aster-ssd` and `attached-milestones` temporarily removed in a local check, the full suite passes. State in the PR that this check was run. | **Deferred to the reviewer removal step under the approved gate narrowing** in [6133101699](https://github.com/tya5/chrona/issues/1402#issuecomment-6133101699): this issue's gate is no retired input reads, not complete permanent-consolidation acceptance. Approved isolated check on `de599109`: 10734 passed, 5 failed, 20 standard skips, 580.17s. The retired gallery key is subsequently fixed with focused evidence. Hosted-DVT and annotation-box witnesses remain reviewer removal prerequisites; two packaged gallery declarations need consolidation cleanup, not retired-input-read fixes. The additional [question](https://github.com/tya5/chrona/issues/1402#issuecomment-6133512564) does not block the already narrowed gate. No full-suite success or express catalogue-assignment claim. |
| No test reads those example paths. A grep check in the PR shows it. | Met for retired input reads: frozen-input AST guard covers split paths in all tests and both tools; approved removal run reveals no retired input loads. Documentary inventories are deliberately not input reads. PR includes the search command and findings. |

Focused fixture/AST/reachability/corpus/gallery/ledger tests: 28 passed. Fixture-only
public materializer check: 10 contexts, 20 declared outputs; all 20 equal current
published counterparts. Ten Scene metadata updates, zero SVG changes. All 739
existing schema probe/document verdicts remain unchanged; fixture paths/baselines
were repointed rather than refreshed to change answers.

Isolated removal state was fully restored: dedicated worktree clean; preserved
backup SHA-256 `9388c586b269c30defd335b7516a871a4f2301f14667b98a19708b446a4d7f6c`.
The [reviewer's consolidation/removal plan](https://github.com/tya5/chrona/issues/1402#issuecomment-6133101699)
is the successor disposition for the original full-removal condition. Catalogue
consistency validates remaining gallery declarations; neither failing test opens
retiring inputs. Preserve those findings without widening this issue back into
the permanent migration. Exact-head CI38317941550 and implementation release
38320123870 succeeded. Close only after this corrected literal review is published
and its exact-main release succeeds; do not claim the original isolated run passed.
