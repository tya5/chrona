# Issue 222 Materialization Reversibility Correction

## Trigger

Specification 51 calls Stage 3 one-way: an explicit workspace has no preset binding
or inheritance edge.  A generic inverse that rewrote it to guided mode would recreate
that removed ownership edge and could silently bind a different preset package.  It is
therefore not a safe undo operation.

## Decision

`materializePresentationPreset` is an explicitly **non-reversible** aggregate command.
An accepted result declares `reversible: false`.  No authoring `undo` or `redo` command
is defined for it.  Git history remains the deliberate review/revert mechanism for a
materialized source bundle; a later user who wants a new guided workspace creates one
through an explicit start/select-preset operation rather than resurrecting receipt
provenance as a live binding.

This uses the non-reversible-operation rule in Specification 10.  Ordinary compact
task/Actual and Stage-2 presentation commands remain eligible for their separately
defined command-history semantics.  The correction does not weaken base-revision CAS,
failure atomicity, or the requirement that no partial candidate becomes visible.

## Acceptance effect

Stage-3 tests must assert the accepted command result declares the limit and that no
undo/redo syntax is admitted for materialization.  Byte-equivalence, explicit-route,
receipt, collision, stale-base, and failure-rollback evidence remain required.
