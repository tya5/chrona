# Architecture Review — Fit Specification Supersession (#457)

**Decision:** approve the [specification amendment](../../design/issue-457-fit-specification-supersession-2026-09-26.md) before L2 publication.

| Normative source | Reconciliation |
| --- | --- |
| Specification 08 | Current v0.5 Layout completion supersedes older Scene measurement and out-of-bounds refusal descriptions; adapter uses the completed canvas. |
| Specification 28 | Detail-panel content uses natural visible geometry and warning when compact placement is impossible. |
| Specification 33 | Valid allocation shortage cannot be a contradictory constraint; the historical required-overflow code no longer has a valid-fit producer. |
| Specification 43 | Typography-aware minima remain measurements, not a required-slot refusal trigger. |
| Specification 44 | Stacked member rows keep mark size and grow naturally; annotation rail uses explicit suppression or visible fallback. |
| Specifications 13/30/50 and ADR-0031 | Immutable resource closure, font measurement identity, and Layout/Scene ownership remain unchanged. |

No compatibility branch is retained to reproduce historical fit rejection.
The implementation amendment removes the dead immutable diagnostic rewrite
and checks both entry paths against the same Layout result.
