# Core Specification v0.1 Stable Readiness Review

**Status:** Review complete  
**Current maturity:** Stable — Date-only scheduling profile

## Executive result

The semantic core is now substantially closed. The latest pass found that the largest
remaining ambiguity was not another primitive but the **conformance boundary** itself.

Core v0.1 is therefore narrowed to a Date-based scheduling profile while retaining
DateTime as a semantic type for future expansion.

## Issues resolved in this pass

### S1 — DateTime scope was underspecified

Resolved by ADR-0011. DateTime remains in the model, but timezone/DST-aware scheduling
is not required for v0.1 conformance.

### S2 — Fixed target dependency authority was underspecified

A dependency targeting fixed placement validates the fixed coordinate and never moves
it. Violation produces `E_FIXED_TARGET_VIOLATION`.

### S3 — Explicit anchor conflict behavior was underspecified

An explicit scheduled anchor is authoritative. A dependency/bound requiring that
endpoint to move creates an inconsistency; the scheduler does not silently override
the anchor.

### S4 — Candidate date vs working-calendar placement was underspecified

Dependency arithmetic produces a raw bound. For a scheduled WorkPeriod target, forward
placement chooses the first valid working date at or after the candidate. Fixed
coordinates are never normalized.

### S5 — WorkPeriod span endpoint counting was underspecified

`start=Monday, amount=1wd` resolves to exclusive `end=Tuesday`. This aligns WorkPeriod
duration with half-open span semantics.

### S6 — Error surface was not stable enough

A normative diagnostic-ID table now distinguishes structural, reference, temporal,
calendar, feasibility, fixed-authority, and warning conditions.

## Stable-promotion evidence

The two required classes are now complete:

1. **Independent implementation validation** — the Date-only scheduler implements the
   conformance fixtures and reports the normative authority/conflict diagnostics.
2. **Schema/example full validation** — the full fixture runner uses `jsonschema` plus
   semantic validation; all canonical fixtures and the pytest suite pass.

No contradiction was exposed, so the Date-only Core v0.1 profile is Stable. Any future
DateTime/DST scheduling profile is a separate compatibility and review decision.

## Non-blocking deferred work

- DateTime scheduling profile;
- uncertainty solver;
- coarse precision syntax;
- snapshot/baseline persistence;
- multi-file merge semantics;
- extension package acquisition;
- presentation implementation, persistence formats, and adapter conformance.

These are explicitly outside the Stable Core v0.1 scheduling contract.
