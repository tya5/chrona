# Chrona implementation checkpoint — 2026-09-17

## Scope

This repository has progressed beyond the initial Core checkpoint. The current,
living specification set is in `timeline-design/`; Git history preserves the earlier
candidate rather than treating the working tree as an unchanged snapshot.

## Included

- `src/chrona/temporal.py`: Date, CalendarPeriod, and WorkPeriod arithmetic.
- `src/chrona/validation.py`: JSON Schema entry point and Core semantic rules.
- `src/chrona/scheduler.py`: Date-only, endpoint-bound, acyclic reference
  scheduler.
- `src/chrona/render.py`: deterministic SVG projection of resolved placements.
- `tests/`: executable checks for temporal conformance and scheduling authority.
- `timeline-design/docs/fixtures/controller-x.yaml`: a rendered semiconductor
  development example, with its derived `controller-x.svg`.

## Verified in this checkpoint

- All canonical CalendarPeriod and WorkPeriod fixture cases pass.
- Valid and invalid scheduled-span amount fixture cases pass.
- Source files compile successfully.
- `pytest` passes with the declared development dependencies.
- The controller example validates, schedules, and renders as SVG.
- Dependency-bound, multiple-bound, and working-day placement cases from the
  Core v0.1 conformance fixture execute through the reference scheduler.
- Every checked-in canonical project example validates structurally and
  semantically, then schedules without an error diagnostic.
- Zero-lag cycles, positive contradictory cycles, fixed-target authority, and
  explicit-anchor conflicts execute with their normative diagnostic IDs.

## Stable promotion

The Date-only Core v0.1 profile is Stable. Full fixture conformance and `pytest` pass
with the declared dependencies; the stable-readiness review records the resulting
scope. Any implementation-discovered ambiguity must still be recorded as an ADR or
diagnostic before changing the Core specification.

The SVG renderer is an intentionally small vertical slice, not the full View,
Style, Theme, or Scene specification. It consumes scheduler output and never
becomes a persisted source of project semantics.

DateTime/DST, rendering, capacity, collaboration, and extension implementations exist
as versioned successor or adapter modules. They do not change Date-only Core v0.1
meaning unless an explicit successor profile is selected.
