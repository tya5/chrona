# Architecture Review — Portable Derived-Artifact Paths (#451)

**Decision:** accept.

This is a protocol-boundary correction, not a filesystem abstraction change.
Keeping `Path` values for local operations preserves platform correctness;
converting the repository-relative identity once at report serialization
prevents the host operating system leaking into CI output.  It satisfies the
#451 requirement for platform-safe deterministic command/report rendering,
does not change artifact validation authority, and introduces no compatibility
or product-layer dependency.
