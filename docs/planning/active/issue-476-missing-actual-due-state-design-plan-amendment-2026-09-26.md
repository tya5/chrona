# Design Plan Amendment — TVAC Fixture Truth (#476)

**Predecessor:** [design plan](issue-476-missing-actual-due-state-design-plan-2026-09-26.md). **Evidence:** public `examples/halcyon-1/actual.yaml` contains `tvac-in-progress` for `projectObjectId: tvac` at `asOf: 2027-08-20`, with a start and progress but no finish. This is a selected observation. The issue's literal boundary-case phrase “`tvac` ... no observation” is therefore false for the committed corpus. The contradiction is raised on [#476](https://github.com/tya5/chrona/issues/476#issuecomment-5845498008); owner disposition is pending.

## Corrected design evidence plan

Keep the shipped Actual fact intact: TVAC is observed but incomplete and must
not receive a missing-Actual mark. Test the inclusive planned-finish boundary
using a characterized HALCYON Actual-set **copy** that removes only the TVAC
observation, plus a synthetic point at the boundary. The issue's two other
criteria can be verified on unmodified HALCYON. Do not delete an observation
from the public corpus to make a sentence in an issue true. If the owner
chooses another interpretation, return to a published design correction before
implementation.

Design must distinguish four states—recorded, due-unobserved, not-yet-due and
unavailable as-of—so the future table cell is not mislabeled “Recorded” and a
summary count without an as-of is not falsely zero. This is the extra design
decision exposed by the issue/code comparison; it is not a hidden compatibility
branch.
