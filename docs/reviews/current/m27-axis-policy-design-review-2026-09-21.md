# M27 Axis Policy Design Review — 2026-09-21

**Decision:** Approved; I27-R2 may implement the versioned ISO axis fit rule.

The rule closes an absent current-resource contract without adding a schema or
silently reviving a legacy setting. It consumes frozen metrics, is generic across
windows/projects, preserves half-open calendar semantics, and diagnoses an impossible
axis rather than emitting the former fixed 28-day labels.
