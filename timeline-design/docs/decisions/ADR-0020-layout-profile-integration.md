# ADR-0020: Layout Profile integrates presentation composition

**Status:** Accepted

## Decision

Introduce one declarative Layout Profile as the composition owner and deprecate the
overlapping M15 table-timeline profile. View keeps semantic selection; Style keeps role
selection; Theme keeps token values; Scene keeps derived geometry.

## Consequences

Existing M15 profile fields migrate into named Layout slots/constraints. The renderer
must reject both profiles in one closure, preventing ambiguous geometry authority. This
adds a solver/manifest but prevents a per-renderer template dialect and preserves
Git-reviewable, AI-proposable resources.
