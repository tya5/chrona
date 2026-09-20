# Chrona implementation checkpoint — 2026-09-20

## Scope

This repository has progressed beyond the initial Core checkpoint. The current,
living specification set is in `docs/specification/`; Git history preserves the earlier
candidate rather than treating the working tree as an unchanged snapshot.

## Included

- `src/chrona/core/temporal.py`: Date, CalendarPeriod, and WorkPeriod arithmetic.
- `src/chrona/core/validation.py`: JSON Schema entry point and Core semantic rules.
- `src/chrona/scheduling/scheduler.py`: Date-only, endpoint-bound, acyclic reference
  scheduler.
- `src/chrona/presentation/render.py`: deterministic SVG projection of resolved placements.
- `tests/`: executable checks for temporal conformance and scheduling authority.
- `conformance/controller-x.yaml`: a rendered semiconductor
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
- The issue-remediation program for GitHub issues 1–10 is complete: Core scheduling,
  reproducible CLI inputs, legacy rendering isolation, content-addressed font metrics,
  and declared presentation-setting consumption are covered by regression evidence.
- M23 Review Detail is complete: schema/semantic validation, Layout-bound group detail,
  source-labelled observations, milestone digest Scene/SVG primitives, and reproducible
  Controller Z visual acceptance all pass without changing scheduling authority.
- Post-M23 presentation regressions #14, #16, and #17 are corrected and closed with
  exact published evidence; Aster and Controller Z artifacts are reproducible.
- The complete test suite passes 248 tests, and the complete Chrona conformance runner
  passes every stage.

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

M22 remediation, M23 review-detail delivery, and the post-M23 issue closure program are
complete. The Aster and Controller Z acceptance SVG/PNG resources are reproducible from
their YAML resources with zero raster overflow.
