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
- `tests/`: executable checks for temporal conformance and scheduling authority.

## Verified in this checkpoint

- All canonical CalendarPeriod and WorkPeriod fixture cases pass.
- Valid and invalid scheduled-span amount fixture cases pass.
- Source files compile successfully.

## Still required for Stable promotion

1. Install the declared development dependencies and run `pytest` in a normal
   Python environment; this Work runtime did not have `jsonschema` or `pytest`
   available at the checkpoint.
2. Extend the conformance runner to cover every scheduling fixture case and
   project-format fixture, including schema diagnostics.
3. Review any implementation-discovered ambiguity as an ADR or diagnostic before
   changing the Core specification.

No DateTime, DST, renderer, or resource-leveling behavior has been introduced.
