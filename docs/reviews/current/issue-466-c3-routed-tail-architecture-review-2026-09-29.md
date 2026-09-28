# #466 C3 routed-tail architecture review

**Reviewed:** [correction](../../design/issue-466-c3-routed-tail-correction-2026-09-29.md), current Specs 02/06/07/08/33/44/50, candidate/topology/corridor designs, #449 fallback, and C4 contrast. **Base:** public `main` `56f65735`; trial resources are not accepted evidence.

| Boundary | Finding |
| --- | --- |
| Project → View | The three note texts remain Project-owned and consumed once. `actual/body` for TVAC describes its actual-lateness note; station remains `planned/finish`. No copied prose or presentation coordinate enters Project. |
| View → Layout | Existing typed `tail` candidate, obstacle classes, as-of side and 1024 box limit remain. View declares intent, not a route. |
| Theme → Layout | Existing balloon geometry and paint role suffice. A missing balloon token remains an error. No extra Theme topology switch is needed. |
| Layout → Scene | Layout chooses direct/routed topology and commits body, triangular tip and strict relation together. Pending-body and source-cluster checks prevent self-penetration or overlap. Scene receives completed geometry/provenance and cannot reroute. |
| Scene → adapters | Existing Balloon path and annotation-leader relation carriers suffice. SVG/typeset serialize both; PNG derives from SVG. The resulting rendered output, not only Scene, is acceptance evidence. |
| Fallback/contrast | Strict tail never bridges a semantic relation. Failed search remains reported visible overflow, not a false fit. C4's same-source note-box ground is unaffected by the added leader relation. |

**Decision:** design accepted for implementation planning, conditional on a focused bounded-search witness under the stated 1024 connector-state limit. The diagnostic witness paths prove geometric possibility but are not proof that the current algorithm finds them. If the finite search cannot find them without weakening bounds or obstacles, stop and amend this design; do not publish a materializer that merely hides an overflow.
