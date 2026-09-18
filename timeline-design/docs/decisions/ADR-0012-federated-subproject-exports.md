# ADR-0012: Federate subprojects through immutable timeline exports

**Status:** Proposed  
**Date:** 2026-09-18

## Context

Large programs contain subprojects with separate leaders, repositories, review
cadence, and edit authority. A program-level timeline must show approved subproject
milestones and progress without requiring every leader to edit a shared Project file.

## Decision

Chrona will model this as federation: a child Project publishes a deliberately small,
versioned timeline export, and the parent stores a typed reference pinned to one
immutable child export revision and content identity. The parent renders a namespaced,
read-only summary projection. It never includes or mutates the child Project source.

## Alternatives considered

| Alternative | Decision | Reason |
|---|---|---|
| One shared Project document | Rejected | It conflicts with independent ownership and produces shared-file coordination pressure. |
| Git submodule/raw child Project loading | Rejected | Separate commits are useful, but a source-tree mount does not define which child facts are public or stable for program aggregation. |
| Centralized portfolio/work-package hierarchy | Rejected | It expands Chrona into a general PM service with centralized operational ownership. |
| Immutable timeline export federation | Selected | It preserves independent history while making parent consumption reproducible and reviewable. |

## Consequences

- A child owns publication, export contents, and its own Commands.
- A parent owns only its federation reference, View selection, and parent-native work.
- An export reference cannot be a branch name or implicit latest revision.
- Published interface milestones may constrain parent work, but no parent operation
  schedules or mutates child internals.
- Before implementation, the export envelope, trust policy, reference command,
  resolver diagnostics, schemas, and positive/negative fixtures require completion.

## References

- [Federated Projects Design](../federated-projects-design.md)
- [Git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
