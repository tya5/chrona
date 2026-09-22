# ADR-0023: Theme v0.2 is the only M25 Theme input

**Status:** Accepted

## Decision

M25 replaces `chrona/presentation/v0.1` Theme with `chrona/theme/v0.3`. Theme v0.2 has no concrete color token and no inheritance. It carries non-color tokens plus a complete role-property-to-Scheme-intent binding map. Render Context v0.5 is the only M25 entry and requires a Color Scheme reference.

## Consequences

The review resolver can prove a single color authority before Scene construction. Legacy review Theme and Context inputs are rejected or removed rather than adapted. The separate core diagnostic SVG is outside this decision. Existing review fixtures move atomically, so this deliberately makes stale authoring files invalid.
