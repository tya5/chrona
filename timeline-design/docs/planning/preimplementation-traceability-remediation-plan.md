# Pre-Implementation Traceability Remediation Plan

**Status:** Active — implementation blocked  
**Authority:** Owns closure order for findings T-01–T-12 from the design/use-case/
milestone consistency review. Semantic changes remain owned by their specifications.

## 1. Completion rule

Implementation may resume only when every Blocker and High finding is closed, the
machine-readable traceability matrix validates, every product design has a user-visible
use case and milestone, every use case has exit evidence, and a renewed final review is
published. Medium findings required by the validation gate must also be complete.

## 2. Ordered phases

| Phase | Findings | Work | Exit evidence |
|---|---|---|---|
| TR-0 — Gate correction | T-08 | Reopen the design-completion claim and mark prior DC-4 authorization historical. | Updated closure program and review disposition. |
| TR-1 — Successor use cases | T-01, T-02, T-03 | **Complete.** Add separate actor/outcome/exception/acceptance use cases for DateTime/DST; resource capacity and explicit leveling; cost/time observations; collaboration conflict resolution; authorization/approval/audit; hosted synchronization. | UC-16–UC-21 and successor traceability entries; `tr-1-successor-use-case-review-2026-09-19.md`. |
| TR-2 — Milestone ownership | T-04, T-05, T-06, T-07, T-10, T-11 | **Complete.** Assign AI integration and Actual ingestion; make M0.5→M1 gating explicit; link FD-4/FD-5 to M8/M9; add post-M9 successor milestones in dependency order; correct the stale post-M9 boundary. | M0.5–M13 roadmap ownership and `tr-2-milestone-ownership-review-2026-09-19.md`. |
| TR-3 — Evidence normalization | T-09, T-12 | Reconcile the UC summary/detailed mapping and add schema/validation for design→UC→milestone completeness, uniqueness, status, and evidence fields. | Valid matrix; deliberately deferred rows carry an explicit owner and gate. |
| TR-4 — Renewed whole-system review | all | Re-run owner, compatibility, use-case, milestone, dependency, and release-claim checks. | Review with no unresolved Blocker/High finding and a new published implementation authorization. |

## 3. Required design choices during remediation

TR-1 and TR-2 must decide, in the owning documents rather than in implementation:

- whether resource/capacity and cost/time observation are one milestone or separate;
- whether collaboration service, policy/approval, and hosted synchronization ship
  together or through explicit sub-milestones;
- whether AI editing belongs in M5, M7, or a dedicated milestone;
- where external Actual ingestion ends and human reconciliation begins; and
- the dependency order of DateTime/DST, resource evaluation, collaboration, extension
  lifecycle, and expanded output releases.

## 4. Publication discipline

Each TR phase is one focused, non-force GitHub `main` publication. Its review records
the published commit and validates that no implementation source changed. A later phase
must not rely on an unpublished predecessor.
