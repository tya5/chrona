# Whole-Design Recompletion Plan

**Status:** Active — implementation frozen pending completion

## 1. Trigger and decision

Implementation was advanced using earlier design-closure reviews without re-running a
complete design-to-delivery gate when an implementation gap was discovered. That is not
an acceptable authorization path. This plan supersedes any per-milestone assumption
that an earlier review alone authorizes later implementation.

No further product implementation is authorized until every item in section 3 is closed
by its owning specification, schema/fixture where it defines exchange data, use-case
mapping, delivery owner, and review evidence.

## 2. Review method

For every design area, review these five links in order:

1. authoritative specification and accepted architectural decision;
2. actor-facing use case, including exceptional behavior;
3. versioned schema and canonical positive/negative fixture where data crosses a boundary;
4. exactly one implementation milestone and explicit reuse boundary; and
5. acceptance evidence that distinguishes delivered, excluded, and future capability.

An earlier implementation is evidence only. It cannot define missing semantics or make
an undocumented capability accepted.

## 3. Closure work

| ID | Area | Gap found | Required design outcome | Owner / dependency |
|---|---|---|---|---|
| WD-1 | Current-profile UC catalogue | **Complete.** | UC-01–UC-15 summary distinguishes delivered, blocked, partial, and future scope. | `14`, M0–M9 |
| WD-2a | Canonical project-field Command | **Complete.** | `setTypedField` has a project target, stable-ID payload, closure validation boundary, and positive/negative schema fixtures. | `10`, `12`, UC-05/06/11, M3/M5 |
| WD-2b | AI proposal and authorization | **Complete.** | Versioned proposal and authorization-decision contracts bind only registered Commands, provenance, policy version, and fingerprint. | `09`, `10`, `12`, UC-06, M5; depends on WD-2a |
| WD-3 | Current-profile release packaging | **Complete.** | Release-package manifest binds artifact, output, and acceptance identities; excluded UC state is explicitly non-publishable. | `22`, UC-13, M9; depends on WD-1/2 |
| WD-4 | Milestone acceptance consistency | **Complete.** | Status ledger states entry/exit evidence and blockers for M0–M13. | roadmap, all milestones |
| WD-5 | Successor designs | **Complete.** | Compatibility ledger records version, opt-in trigger, unchanged v0.1 meaning, migration/rejection rule, and owner for FD-1–FD-5. | `18`–`22`, M8–M13 |
| WD-6 | Whole-system authorization | Earlier closure reviews conflict with WD-1–WD-5 and must not remain an authorization source. | Produce a replacement review with a machine-checkable closure checklist; retain prior reviews as historical evidence only. | depends on WD-1–WD-5 |

## 4. Execution order

1. WD-1 and WD-4 establish honest current delivery state.
2. WD-2a closes the canonical project-field Command contract; WD-2b then closes the
   AI proposal and authorization boundary over that registered vocabulary.
3. WD-3 closes release packaging against the corrected UC set.
4. WD-5 verifies successor isolation and compatibility.
5. WD-6 re-runs the whole-system design authorization review.

Each completed item is validated, reviewed, committed, and published to `main` before
the next item. Only after WD-6 passes may implementation resume; implementation then
follows the revised milestone ledger rather than the prior apparent progress order.
