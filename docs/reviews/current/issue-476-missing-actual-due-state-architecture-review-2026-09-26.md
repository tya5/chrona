# Architecture Review — Due-State Missing Actual (#476)

**Design:** [selected contract](../../design/issue-476-missing-actual-due-state-design-2026-09-26.md). **Plan amendment:** [TVAC source-truth correction](../../planning/active/issue-476-missing-actual-due-state-design-plan-amendment-2026-09-26.md).

| Adjacent authority | Consistency finding |
| --- | --- |
| Project/Scheduling/Actual | Due is compared with canonical planned dates and the declared Actual as-of; no rescheduling or observation repair. |
| Specification 06 View projection | One typed aligned state is derived before any table, summary, Layout or Scene work. |
| Specifications 08/39 Layout and Scene | Layout consumes the completed state and owns mark geometry; Scene emits completed primitives, correcting older Scene-ownership prose. |
| Specifications 25/46 summaries | Count is due-unobserved, and unavailable as-of cannot falsely become zero. |
| #49 typed presentation contract | No later layer parses raw Actual entries or infers absence from an empty dictionary. |
| #470/diagnostic honesty | Shipped TVAC remains recorded-but-incomplete; its diagnostic is not suppressed to satisfy #476's mistaken fixture sentence. |
| Explicit/shared/snapshot rows | Primary state follows the same item through row composition; snapshot/scenario-only items never gain a Primary missing-Actual mark. |

**Decision:** approved for implementation planning, subject to the issue
owner's clarification of the literal TVAC fixture sentence before final issue
closure. The rule and migration can be implemented and verified without that
wording change. The principal risk is a parallel `not bool(actual)` check left
in table, summary or Layout; structural search and focused tests must close
every consumer. Living Specifications 06, 08, 25, 39 and 46 are amended in the
same published design phase; no ADR is needed because the due-state rule is a
local correction to their existing comparison contract.
