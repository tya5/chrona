# ADR-0015: Resource leveling is an explicit proposal

**Status:** Accepted for proposed successor design

## Decision

Capacity infeasibility yields diagnostics and an optional derived leveling proposal.
It never mutates Project placements automatically. A typed Command applies an accepted
proposal against a current Store revision.

## Consequence

Plan demand, capacity, actual effort, and accounting observations retain separate
authority and audit trails.
