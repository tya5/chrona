# ADR-0025: Bind operational automation to complete immutable references

**Status:** Accepted  
**Date:** 2026-09-21

## Context

The v0.1 command document combines a raw target path with a revision token. The
product `propose-set` path reads a working-tree file and does not persist a CAS result.
That is unsuitable for repeatable CI or safe retries.

## Decision

M26 introduces `chrona/command/v0.2`. Its target is a complete provider-neutral
Revision Store resource reference; its declared base revision and expected content
identity must equal the reference. Automation emits one versioned result envelope and
records a canonical request identity for replay. A check never writes; apply delegates
the one named mutation to the Store's CAS operation.

The v0.1 document is not changed. `propose-set` is removed, without an alias, when the
v0.2 product path is implemented.

## Consequences

- CI jobs can reproduce their inputs without a repository checkout or branch default.
- Callers must construct verified references before they mutate, increasing adapter
  work but removing ambiguous target selection.
- Command ID reuse is detectable and cannot apply a different request accidentally.
