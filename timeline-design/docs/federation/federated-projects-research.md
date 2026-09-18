# Federated Subproject Research

**Status:** Reviewed input to ADR-0012  
**Question:** How can a program consume subproject timelines without shared mutable
source files?

## Findings

| Product pattern | What it demonstrates | Chrona implication |
|---|---|---|
| Git submodules | A superproject can pin another repository at a particular commit while histories remain separate. | Use immutable identities, but do not treat a checked-out source tree as a timeline contract. |
| Integrated project/portfolio tools | Central project lists, hierarchy, work tracking, and portfolio views support top-down coordination. | Do not import their centralized operational model; Chrona should remain an explicit timeline projection tool. |

## Design inference

Chrona needs a stable *publication boundary*, not recursive inclusion of arbitrary
Project files. A child timeline export can expose selected public milestones, status,
and interface commitments while preserving child-private planning detail and independent
review. The parent consumes one approved revision, records it in the evaluation closure,
and receives diagnostics instead of silently following a branch tip.

## Sources

- Git: [Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- OpenProject: [Project lists](https://www.openproject.org/docs/user-guide/projects/project-lists/)
