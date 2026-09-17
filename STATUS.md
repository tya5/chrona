# Chrona implementation checkpoint — 2026-09-17

## Scope

This is an initial, repository-ready implementation checkpoint for the Core v0.1
Stable Candidate. The canonical specification snapshot in `timeline-design/` is
preserved unchanged.

## Included

- `src/chrona/temporal.py`: Date, CalendarPeriod, and WorkPeriod arithmetic.
- `src/chrona/validation.py`: JSON Schema entry point and Core semantic rules.
- `src/chrona/scheduler.py`: Date-only, endpoint-bound, acyclic reference
  scheduler.
- `src/chrona/render.py`: deterministic SVG projection of resolved placements.
- `tests/`: executable checks for temporal conformance and scheduling authority.
- `timeline-design/docs/examples/controller-x.yaml`: a rendered semiconductor
  development example, with its derived `controller-x.svg`.

## Verified in this checkpoint

- All canonical CalendarPeriod and WorkPeriod fixture cases pass.
- Valid and invalid scheduled-span amount fixture cases pass.
- Source files compile successfully.
- `pytest` passes with the declared development dependencies.
- The controller example validates, schedules, and renders as SVG.

## Still required for Stable promotion

1. Extend the conformance runner to cover every scheduling fixture case and
   project-format fixture, including schema diagnostics.
2. Review any implementation-discovered ambiguity as an ADR or diagnostic before
   changing the Core specification.

The SVG renderer is an intentionally small vertical slice, not the full View,
Style, Theme, or Scene specification. It consumes scheduler output and never
becomes a persisted source of project semantics.

No DateTime, DST, renderer, or resource-leveling behavior has been introduced.
