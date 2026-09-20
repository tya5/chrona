# M11 Capacity and Accounting Implementation Readiness Plan

**Status:** Complete — design closure before runtime.

M11 uses explicit Date-only daily availability, constant per-day span demand, the sole
declared objective, forward-only stable-ID leveling, and complete fingerprint-bound
proposals. Cost observations are a separate append-only resource.

| Phase | Scope | Exit evidence |
|---|---|---|
| M11-1 | Validate capacity resources and derive overloads. | unit/reference/duplicate availability tests; no Project mutation. |
| M11-2 | Produce/apply deterministic proposals through CAS. | fixed/anchor/scope/stale/partial rejection tests; regression. |
| M11-3 | Store and aggregate cost observations separately. | unit/rate, duplicate/stale, and schedule-isolation tests. |
| M11-4 | UC-17/18 and reuse/release review. | full suite and conformance evidence. |
