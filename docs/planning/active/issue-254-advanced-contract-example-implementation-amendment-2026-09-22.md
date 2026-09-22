# Issue 254 Advanced-Contract Example Implementation Amendment

**Amends:**
`docs/planning/active/issue-254-advanced-contract-example-implementation-plan-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issue-254-advanced-contract-example-design-correction-2026-09-22.md`

E254-1 remains one atomic materializable-evidence PR. Replace its original
`flight-readiness` Project members with the `mission-closeout` rollup and the
FRR → Launch → LEOP → First-light critical chain; bind
`contexts/06-flight-readiness.yaml` to the existing `briefing` Layout Profile;
and assert the three resulting `dependency-critical` primitives plus the FRR
title-cell link. The WBS, float, Scenario provenance, full-manifest discovery,
six-slide materializer reproduction, prior-hash comparison, focused tests, and
full-suite gate are unchanged.

No Layout feasibility behavior or scheduler analysis is modified. The amendment
only corrects authored inputs so E254-1 can prove the previously specified
released contracts.
