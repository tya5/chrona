# Design, Use-Case, and Milestone Consistency Review

**Date:** 2026-09-19  
**Disposition:** Fail — implementation remains blocked pending traceability remediation.

## 1. Review scope and method

The review traces every current and successor design area through four required links:

1. one authoritative specification;
2. at least one user-visible use case with normal, exceptional, and acceptance paths;
3. one implementation milestone that owns the complete deliverable; and
4. one exit-evidence statement capable of proving the use case at that milestone.

The machine-readable result is
`../traceability/design-usecase-milestone-v0.1.yaml`. An empty use-case or milestone
list is a blocking gap unless the design is explicitly non-product governance.

## 2. Coverage summary

| Area | Specification | Use case | Milestone | Result |
|---|---|---|---|---|
| Core Date-only planning | `02`–`05` | UC-01 | M0 | Covered |
| Self-hosted delivery profile | `17` | UC-15 | M0.5 + M1 resolution edge | Partial: split completion is not represented as an explicit gate |
| Revision Store | `15` | UC-02/04/09/12/14/15 | M1 | Covered |
| Presentation and projection | `06`–`08`, `13` | UC-03/04/09/13 | M2, M6, M9 | Covered |
| Controlled semantic mutation | `09`, `10` | UC-05/06/10/12 | M3, M5, M7 | Partial: AI and ingestion adapters have no milestone deliverable |
| Federation | `16` | UC-14 | M4 | Covered |
| Automation/CLI | `09`, `10` | UC-11 | M5 | Covered |
| Interactive annotations/editing | `06`, `08`, `10` | UC-05/08/10/12 | M7 | Partial: reconciliation UI is covered, external Actual ingestion is not |
| Extension lifecycle | `11`, `21` | UC-07 | M8 | Partial: FD-4 linkage and lifecycle acceptance are not stated in M8 |
| Output/release | `22` | UC-13 | M9 | Partial: FD-5 linkage is implicit, and M9 overclaims all UC-01–UC-15 |
| DateTime/DST successor | `18` | none | none | Missing |
| Resource/capacity/leveling/cost successor | `19` | none | none | Missing |
| Collaboration/sync/merge/audit successor | `20` | none | none | Missing |

## 3. Blocking findings

| ID | Severity | Finding | Consequence |
|---|---|---|---|
| T-01 | Blocker | FD-1 DateTime/DST has no actor-driven use case or milestone. | Its acceptance evidence cannot be connected to a releasable outcome. |
| T-02 | Blocker | FD-2 combines capacity, leveling, cost, and timesheets without user-use-case decomposition or milestone ownership. | A future implementation could silently choose scope or mix plan and observation authority. |
| T-03 | Blocker | FD-3 collaboration, authorization, approval, audit, and hosted sync have no use case or milestone. | Conflict and policy semantics cannot be accepted end-to-end. |
| T-04 | Blocker | UC-06 requires an AI adapter/policy integration, but M5 owns only CLI/automation and no later milestone owns AI. | M9 cannot honestly claim UC-06 acceptance. |
| T-05 | Blocker | UC-10 requires external Actual ingestion, while M6/M7 own review/reconciliation only. | The trigger path into the designed Actual model is unowned. |
| T-06 | Blocker | M9 claims UC-01–UC-15 acceptance although T-04 and T-05 remain unowned. | The release exit condition is internally impossible. |
| T-07 | Blocker | Roadmap section 4 says DateTime, resource, and collaboration still require design, although FD-1–FD-3 are complete. | The roadmap contradicts the canonical successor design state. |
| T-08 | Blocker | The previous DC-4 review checked owner boundaries but not complete design→UC→milestone chains. | Its implementation authorization is invalidated. |

## 4. Non-blocking but required corrections

| ID | Priority | Finding | Required correction |
|---|---|---|---|
| T-09 | High | The UC summary table still describes several schemas/fixtures as deferred although later evidence exists. | Regenerate the summary from the detailed evidence mapping. |
| T-10 | High | M0.5 is ordered before M1 but declares completion through M1 package resolution. | Split the gate or state an explicit provisional/completion dependency. |
| T-11 | High | FD-4 and FD-5 semantically map to M8 and M9, but those milestone rows do not cite the successor owners or full diagnostics. | Make the ownership and acceptance links explicit. |
| T-12 | Medium | No machine-check enforces that every product design has a use case and every use case has milestone ownership. | Add a traceability schema and validation gate. |

## 5. Decision

The individual design specifications remain useful and their focused reviews are not
discarded. However, the project is not ready to resume implementation. The final design
gate is reopened until T-01–T-12 are closed in dependency order and a renewed review
passes the structured traceability matrix.
