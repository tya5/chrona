# Architecture Review — Literal Issue Acceptance and Close Disposition (#438)

**Decision:** Accepted for implementation planning.

The design keeps GitHub as issue authority and repository reviews as immutable
evidence.  It avoids a second issue tracker, runtime dependency on GitHub, or
heuristic parsing of prose.  The finite matrix makes a release claim auditable
while keeping programme criteria additive.  The close-comment requirement
preserves the public trail when an issue's literal goal is narrowed or moved.
