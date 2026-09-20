# M24 Source Adapter Design Addendum — 2026-09-20

**Decision:** PASS — I24-4 may resume after this addendum is published.

## Finding

The first I24-4 path audit found that Specification 33 closed outer source placement but
did not say how source-internal row, mark, axis, text, and legend quantities survive the
deletion of Presentation Settings. Implementing without a correction would retain the old
aggregate as a translation layer or move its numbers into renderer defaults. Both outcomes
would violate ADR-0023 and the no-compatibility decision.

## Completed design

- Layout Manifest has exclusive authority over source rectangles.
- Each source has a pure measure/compose adapter; the exact measured result used by Layout
  is frozen and reused during composition.
- View supplies semantic modes; Theme supplies concrete visual quantities; Scene contains
  the resulting source-linked primitives.
- Theme gains optional `metrics`, mapping closed semantic metric names to declared number
  tokens. Layout distances and adapter metrics can reuse the same token.
- Missing, unknown, or wrong-type metric bindings diagnose. Renderers have no author-
  tunable numeric fallback table and do not read Layout YAML.
- Adapter metric namespaces are closed by component, preventing arbitrary settings bags.

## Review

This boundary preserves fact selection, styling, composition, and serialization ownership;
removes the need for a legacy adapter; and gives measurement and composition identical
inputs. It introduces no coordinate authoring and no second layout authority. The Theme
schema extension is additive only to the target design; compatibility is not a goal.

The corrected Specification 33, Theme specification/schema, and I24-4 plan are sufficient
to resume implementation. No product choice remains open.
