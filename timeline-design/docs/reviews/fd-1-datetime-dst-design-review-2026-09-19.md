# FD-1 DateTime/DST Design Review — 2026-09-19

**Status:** Review complete  
**Scope:** DateTime/timezone/DST/recurrence successor and Date-only compatibility.

| Gate | Result | Evidence |
|---|---|---|
| Date-only compatibility | Pass | v0.1 syntax and scheduling remain unchanged; conversion is explicit and versioned. |
| Timezone authority | Pass | instant comparison and IANA zone-local calendar semantics have separate explicit roles. |
| DST determinism | Pass | folds require earlier/later/reject; gaps reject without a silent shift. |
| Scheduling boundary | Pass | mixed-domain components reject; recurrence remains derived input. |
| Persistence/migration | Pass | migration is opt-in, provenance-bearing, and does not assume midnight; nonrepresentable downgrade rejects. |
| Design conformance | Pass | Temporal, Scheduling, Project Format, Quality, schema, fixtures, and ADR use one successor contract. |

## Decision

FD-1 design is complete. No DateTime/DST runtime implementation is authorized until a
separate implementation plan selects this successor profile and its fixture suite.
