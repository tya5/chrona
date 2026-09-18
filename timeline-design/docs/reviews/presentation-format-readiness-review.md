# Presentation Format Readiness Review

**Status:** Review complete
**Scope:** `06`–`10`, `13`, and the Presentation schema handoff.

## Conclusions

- Core Project Format remains the only owner of project, temporal, and scheduling
  syntax; none of the Presentation resources copy or alter it.
- Render Context is the sole evaluation entry point. It binds immutable Project input,
  View, Style, Theme, Scene profile, viewport, target, and metrics explicitly.
- View selects and compares semantic facts; Style maps those facts to roles; Theme maps
  roles to tokens; Scene profile maps projection intent to layout policy. No layer owns
  another layer's authority.
- Snapshot is an immutable Project reference. Actual is independently revisioned
  observation data and cannot reschedule plan. Command is a revision-bound request
  document, not a composable presentation resource.
- Locality is preserved: Actual changes affect comparison facets and dependent Scene
  nodes; token-only changes use `tokenUpdate`; global replacement needs a declared
  View/Style/Theme/viewport/scale or dependency-closure reason.

## Schema readiness

Structural schemas may now be added in this order: Scene profile, Snapshot reference,
Actual set, Style, then Command request. Semantic validation still needs explicit
diagnostics for missing/unmatched Actual, invalid Snapshot revision, unsatisfied View
comparison requirements, and unsupported target capabilities.

## Deferred deliberately

DateTime/DST, font-metric payload acquisition, non-linear scales, selector expressions
beyond the v0.1 closed form, Theme inheritance, command authorization, and renderer
import remain out of scope. They must not be silently accepted by a v0.1 loader.
