# M5.5 Observed Actual Intake Reuse Review

**Date:** 2026-09-19  
**Status:** Review complete

## Scope and design inputs

This review accepts only the M5.5 source-intake adapter. It implements the boundaries
already owned by [Command Model](../../specification/10-command-model.md),
[Presentation Format](../../specification/13-presentation-format.md), and
[UC-10](../../specification/14-use-case-catalog.md). It does not introduce a source
connector, automatic matching rule, Project mutation, schedule recalculation, or an
interactive reconciliation UI.

## Acceptance and reuse check

| Check | Result | Evidence |
|---|---|---|
| Stable external identity | Pass | Every source record requires `source_system` plus `externalKey`; duplicate pairs reject. |
| Explicit resolution only | Pass | A supplied `projectObjectId` is emitted only if it is a known stable Project ID. Text fields are ignored. |
| Visible unmatched handoff | Pass | Unknown or omitted mapping emits `externalIdentity`, `alignment: unmatched`, and `E_ACTUAL_UNMATCHED`. |
| Actual/plan authority separation | Pass | The adapter returns an independently versioned Actual-set body and never accepts a Project, Store, Command executor, or scheduler. |
| M7 handoff | Pass | Each unmatched observation has the exact identity required by the later `resolveActualObservation` Command. |
| Executable inheritance | Pass | `tests/unit/chrona/presentation/model/test_actual_intake.py` joins the complete preceding test and conformance suite. |

## Changed-code classification

| Path | Classification | Reason |
|---|---|---|
| `src/chrona/presentation/model/actual_intake.py` | adapter | Converts explicit external facts to the existing Actual-set contract only. |
| `tests/unit/chrona/presentation/model/test_actual_intake.py` | acceptance evidence | Proves resolved/unmatched behavior and rejects implicit title matching. |

## Decision

M5.5 is complete. M7 may provide reconciliation interaction only by translating the
reviewer's selected stable IDs into the existing Actual Command family; it may not add
another intake or alignment authority.
