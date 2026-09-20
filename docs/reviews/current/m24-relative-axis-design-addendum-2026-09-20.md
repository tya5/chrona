# M24 Relative-Axis Design Addendum — 2026-09-20

**Decision:** PASS — required correction published before I24-3 implementation.

## Finding

I24-2 implementation review found that a guide or barrier defines one axis, while the
original anchor target used one reference for both axes. The accepted example attempted
to use an inline barrier and its block center, but an inline barrier has no block
coordinate. The design could not unambiguously resolve that YAML.

## Correction

Anchor targets and gaps are now axis-specific:

```yaml
anchor:
  self: {inline: start, block: center}
  target:
    inline: {ref: barrier:label-end, point: end}
    block: {ref: parent, point: center}
  gap:
    inline: {token: spacing.m}
```

Each guide/barrier reference must match its declared axis. Parent and node targets may
be used independently on either axis. A gap is optional per axis and is invalid for a
center-to-center relationship on that axis.

## Review

- This removes ambiguity without adding coordinates or arbitrary expressions.
- The model is more reusable because horizontal and vertical relationships can name
  different semantic references.
- Dependency and cycle analysis operates on `(node, axis)` edges, then combines the two
  resolved coordinates into one rectangle.
- Specification 33, schema, and the relative fixture agree.
- No I24-3 production code existed when this correction was made.

