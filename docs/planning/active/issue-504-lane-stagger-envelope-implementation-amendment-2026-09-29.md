# Implementation amendment — finite lane stagger envelope (#504)

This amends the [R2a plan](issue-504-501-lane-label-search-implementation-amendment-2026-09-29.md) after the [design correction](../../design/issue-504-lane-stagger-envelope-correction-2026-09-29.md) and [whole-architecture review](../../reviews/current/issue-504-lane-stagger-envelope-architecture-review-2026-09-29.md). R2's other boundaries and the literal #504 acceptance criteria remain unchanged.

| Publishable unit | Owners and verification |
| --- | --- |
| R2a code and public evidence | `layout/lane_label_intent.py`, `lane_label_preflight.py`, `lane_subtracks.py`, `labels.py`, `surface_composer.py`, `surface_quality.py`, `engine.py`, the internal use-case/Scene-build handoff, and focused tests: share measured intent; take the maximum of interval demand and one measured level plus gap per selected label; keep full-band contact search lane-only; validate typed suppression/short-source facts. Change only 02/12's standalone wallboard profile and 11's overlay profile to `fill`; retain shared wallboard `pack`. Regenerate 02/11/12 Scene/SVG and corpus coverage. Assert 26/26 names and zero suppressions on 02; report 11/12; byte-check 04/07/15 and all public materializers in one batch. Review geometry and generated diffs, then PR CI on the repository matrix. |
| R2a acceptance | Publish a literal #504 review with code/merge SHA, CI, exact shown/suppressed counts, capacity/obstruction evidence where applicable, and all four issue criteria. A remaining 02 suppression stops acceptance and returns to design. Do not close #504 until subsequent R5/public release evidence is complete. |

The R2 code PR must follow the design and this plan's publication. Do not include unrelated preset or default-table changes in the R2 PR.
