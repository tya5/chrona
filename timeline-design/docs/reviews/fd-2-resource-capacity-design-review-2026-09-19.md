# FD-2 Resource, Capacity, Leveling, and Cost Design Review

**Date:** 2026-09-19  
**Disposition:** Accepted for the future-capability implementation gate

## Evidence reviewed

- `19-resource-capacity-successor.md` defines ownership, explicit evaluation, and
  plan/actual/cost separation.
- `ADR-0015-resource-leveling-is-explicit-proposal.md` records the irreversible
  choice that capacity infeasibility is diagnostic/proposal, never an automatic write.
- `resource-capacity-v0.2.schema.yaml` and `resource-capacity-v0.2.yaml` cover
  stable resource/assignment identity, dimension mismatch, overload, stale proposal,
  and cost-observation isolation.
- Project Format, Command Model, and Quality now name the successor serialization,
  command, and invariant boundaries.

## Ownership and compatibility result

Resource capacity is a separately revisioned planning input. A Project remains the
owner of demand declarations and the only owner of accepted schedule changes.
Leveling is a derived evaluation, while Command owns acceptance with the current Store
revision. Actuals, costs, and timesheets are independent observation stores. Scene and
renderer state neither decides nor persists a leveling outcome.

Existing Date-only Projects and ordinary scheduling retain their prior behavior because
capacity is never an implicit scheduler input. The required deterministic ordering is
the declared objective followed by stable object ID; any future alternative must be a
versioned objective and fixture update.

## Review result

No unresolved ownership, hidden auto-leveling, actual-driven rescheduling, or
compatibility migration issue was found. FD-2 may be marked complete; this is design
evidence only and does not authorize resource-leveling implementation before the full
FD-1 through FD-5 gate completes.
