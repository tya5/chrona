# DC-3 Successor-Capability Design Closure Review

**Date:** 2026-09-19  
**Disposition:** Complete — all planned successor capabilities have design closure.

## Cross-phase result

| Phase | Successor owner | Compatibility and authority result | Evidence |
|---|---|---|---|
| FD-1 | `18` DateTime/DST | Date-only remains unchanged; instant/zone and DST fold/gap rules are explicit. | ADR-0014, v0.2 schema/fixture, FD-1 review |
| FD-2 | `19` resource/capacity | Capacity is explicit; leveling is derived/proposed and never an implicit schedule write. | ADR-0015, v0.2 schema/fixture, FD-2 review |
| FD-3 | `20` collaboration | Immutable revisions, typed conflicts, authorization provenance; no last-writer-wins. | ADR-0016, v0.2 schema/fixture, FD-3 review |
| FD-4 | `21` extension lifecycle | Immutable declarative closure, explicit compatibility and failure; no package code execution. | ADR-0017, v0.2 schema/fixture, FD-4 review |
| FD-5 | `22` output/release | Scene adapters declare capability/fidelity and cannot become semantic authority. | ADR-0018, v0.2 schema/fixture, FD-5 review |

## Boundary verification

No successor silently changes the current Date-only scheduling profile, converts a
derived result into canonical state, grants an adapter mutation authority, or relies on
an implicit latest revision. Each successor specifies its opt-in versioning and rejects
mixed or unavailable inputs with a deterministic diagnostic. The required evidence is
design/conformance evidence only; it does not authorize a runtime, service, client, or
output implementation.

## Decision

FD-1 through FD-5 remain separately versioned successors, but their semantics and
migration boundaries are complete. DC-4 may make the final pre-implementation decision
after reconciling this result with the documented product roadmap and explicit deferrals.
