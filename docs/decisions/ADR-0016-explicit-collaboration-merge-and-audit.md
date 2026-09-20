# ADR-0016: Collaboration uses explicit merge, approval, and audit provenance

**Status:** Accepted  
**Date:** 2026-09-19

## Context

Multiple writers and hosted synchronization introduce stale requests, conflicting
semantic changes, and authorization requirements. Treating a hosted tip or renderer
state as authority would violate Store and Command invariants.

## Decision

Chrona collaboration preserves Store-issued immutable revisions and Command
compare-and-set semantics. Stale writes reject or produce a typed merge proposal;
there is no last-writer-wins fallback. Merge conflicts are first-class, auditable
objects resolved by Command. Authorization and approval bind an actor and exact
Command fingerprint before persistence; audit evidence is append-only provenance.

## Consequences

Hosted systems must preserve revision/content identities and conflict/audit records.
They cannot silently coerce semantic changes. Presence and synchronization progress
remain ephemeral. This adds explicit UX and policy work, but preserves reproducibility,
reviewability, and independent federation ownership.
