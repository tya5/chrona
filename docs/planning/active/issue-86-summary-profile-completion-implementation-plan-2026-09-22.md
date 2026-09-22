# Issue 86 — Summary Profile Completion Implementation Plan

**Status:** Approved implementation plan.  **Issue:** #86.
**Design authority:** `issue-86-summary-profile-completion-design-review-2026-09-22.md`.

## Scope and invariant

This plan makes a bound summary profile a consumed, measured, Layout-placed
input to the existing public review route.  It retains one semantic resolver,
one measurement pass, one `SurfaceLayoutRequest → SurfacePlacement` handoff,
and Scene/renderer projection-only responsibilities.

## C86-1 — Resolve summary facts and measure actual runs

**Files:**

- `src/chrona/presentation/review/v05_content.py`
- `src/chrona/presentation/model/surface_content.py`
- `src/chrona/presentation/layout/sources.py`
- `src/chrona/usecases/render_review.py`
- focused unit tests for review content, source measurement, and render-usecase
  closure-read accounting.

**Work:**

1. Add immutable panel/run records and one summary resolver from a validated
   profile, projection, and actual facts.
2. Make final surface-content normalization accept the resolved summary value,
   not the profile mapping, and carry it as its required completed field.
3. Extend source inputs with ordered, role-specific runs and measure their
   actual width, cumulative block advance, and first baseline.
4. Resolve the summary once after projection, record its optional closure
   resource as read, and use its runs for the summary slot before `solve_layout`.

**Acceptance:** no summary YAML is parsed twice; a bound summary profile is
read even when the selected Layout has no summary slot; mixed role runs have
the correct cumulative measurement; unchanged non-summary source measurements
retain their values.

## C86-2 — Place runs and adapt the public authoring closure

**Files:**

- `src/chrona/presentation/layout/surface_composer.py`
- relevant Scene/projection tests only if the new normalized records require
  type adaptation
- `examples/halcyon-1/themes/wallboard.yaml`
- `examples/halcyon-1/generated/02-programme-board.svg`
- `tests/acceptance/output/known_unused.yaml`
- `tests/acceptance/output/known_failures.yaml`
- focused layout, output-property, and public materializer tests.

**Work:**

1. Place the canonical summary run sequence with each run's own typography
   advance and preserve existing placement IDs/semantic purposes.
2. Ensure `figures` values use the `metric` role and captions the `summary`
   role without overlap, while Layout retains overflow/collision responsibility.
3. Add the missing wallboard `metric.fill` role binding; do not add a fallback
   in Layout, Scene, or SVG.
4. Regenerate the programme-board SVG only through the public materializer;
   remove all `summary-profile` unused-input pins and only the #86-owned
   `summary` slot output-property pin.

**Acceptance:** the programme-board emits its declared summary primitives;
all three HALCYON summary-profile bindings are consumed; no title/summary/notes
collision occurs; no unrelated output-property fingerprint changes.

## C86-3 — Verification and publication gate

Run, in order:

1. focused unit tests for summary normalization, source measurement, Layout
   placement, and typed closure read accounting;
2. output-property and closure-consumption acceptance tests;
3. full `.venv/bin/python -m pytest`;
4. conformance and `tools/check_module_reachability.py` / import-direction
   checks;
5. all five public materializer checks, followed by a generated-SVG diff;
6. a structure review confirming that Scene imports neither font metrics nor
   routing and renderer adapters receive completed primitives only.

Before merge, compare the branch with freshly fetched remote `main`, inspect the
exact generated artifacts and target commit, wait for required CI, and merge
without force push.  Publish one implementation PR containing C86-1 through
C86-3 because the source measurement change and the authoring correction must
land atomically to preserve materializability.

## Out of scope

Do not change View/summary schema syntax, Layout Profile grammar, legend
authoring, label policy, table formatting, monochrome treatment, output target
selection, or any #85 fingerprint other than the summary slot resolved here.
