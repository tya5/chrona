# ADR-0021: Maintain a living versioned specification and remediate accepted contracts

**Status:** Accepted

## Decision

`docs/specification/` is Chrona's current, living, versioned specification set. Git history,
release manifests, and versioned schemas preserve earlier states; the working directory
is not described as a verbatim frozen import.

Defects found after milestone acceptance reopen the affected acceptance evidence. They
are repaired through a design-first remediation phase before new deferred milestones
are implemented. Compatibility changes to a stable schema require either restoration of
the accepted form or an explicitly versioned migration contract.

## Consequences

Repository manifests and top-level status documents must point to current artifacts.
Validation attestations state their scope and cannot imply that the entire product was
validated by a narrower fixture runner. M23 remains deferred while issues 1–10 repair
already accepted Core, application, and presentation contracts.
