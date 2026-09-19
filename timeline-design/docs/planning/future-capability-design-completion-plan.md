# Future Capability Design Completion Plan

**Status:** Active design gate  
**Authority:** This plan owns design order and completion evidence only. Each semantic
decision remains owned by its applicable specification.

## Purpose

Before further product implementation, complete the design needed to evolve Chrona
beyond the Date-only, single-writer, declarative-profile product without discarding the
shared Core, Revision Store, Command, and Scene contracts.

## Compatibility invariants

Every future design MUST preserve these unless its owning specification explicitly
versions a successor:

1. Existing Date-only Project documents retain their current scheduling meaning.
2. Store-issued revision identity and content identity remain the reproducibility boundary.
3. GUI, CLI, and AI mutations continue through Command; no collaboration or renderer
   state becomes canonical Project state.
4. Scene remains derived from explicit evaluation inputs; it is never temporal truth.
5. Federation children remain independently owned, pinned, and read-only to parents.

## Ordered design phases

| Phase | Design scope | Owning artifacts to complete | Exit evidence |
|---|---|---|---|
| FD-1 | DateTime, timezone, DST, recurrence and backward-compatible temporal versioning | Temporal Model, Scheduling Model, Project Format, Quality, schemas, positive/negative fixtures, ADR | Date-only compatibility matrix; DST ambiguity/nonexistence rules; deterministic cross-zone examples; review. |
| FD-2 | Resource/capacity, calendars, leveling and cost/time accounting boundary | Domain, Scheduling, Project Format, Quality, schemas, fixtures, ADR | Authority table separating plan/actual/capacity; no hidden auto-leveling; deterministic infeasibility/leveling examples; review. |
| FD-3 | Collaboration, hosted synchronization, merge, authorization and audit provenance | Revision Store, Application Architecture, Command Model, Quality, Federation, schemas, fixtures, ADR | Explicit concurrency/merge policy; approval/audit model; conflict fixtures; no last-writer-wins; review. |
| FD-4 | Extension lifecycle: registry, acquisition, compatibility, cyclic/missing package policy, and code-plugin exclusion | Extension Model, Revision Store, Application Architecture, schemas, fixtures, ADR | Declarative package lifecycle and trust rules; compatibility/inheritance/cycle fixtures; review. |
| FD-5 | Output expansion and release boundary | Scene/Rendering, Application Architecture, Use Cases, Quality, release acceptance plan | Target capability matrix, fidelity-loss diagnostics, UC-01–UC-15 acceptance mapping; final cross-document review. |

## Implementation gate

No implementation phase after the current published M7 gesture adapter may begin until
FD-1 through FD-5 are complete and a design-completion review records that the above
compatibility invariants, schemas, fixtures, ADRs, and cross-document ownership checks
are satisfied. A discovered semantic ambiguity returns work to its owning phase; it is
not resolved in implementation.

## Completion rule

The gate is complete only after every phase has its named specification changes,
machine-checkable schema/fixture evidence, ADR where a compatibility choice was made,
and one final review with no unresolved ownership or migration issue.
