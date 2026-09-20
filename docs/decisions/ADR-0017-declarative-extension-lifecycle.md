# ADR-0017: Extension lifecycle is pinned declarative package resolution

**Status:** Accepted  
**Date:** 2026-09-19

## Decision

Extension packages resolve from configured trusted registries to an immutable,
content-identified declarative closure. They have explicit lifecycle states and reject
missing, cyclic, conflicting, untrusted, or incompatible dependencies. Upgrades and
migrations are explicit Command-governed operations. Host code plugins remain a
separate installed capability and cannot execute from Project/package data.

## Consequences

Evaluations are reproducible and code-free at the semantic package boundary. Registry
and host implementations must expose diagnostics and trust policy, but cannot silently
upgrade or substitute packages.
