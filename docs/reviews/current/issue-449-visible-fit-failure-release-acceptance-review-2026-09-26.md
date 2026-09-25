# Release Acceptance Review — Visible Fit and Placement Failures (#449, #400)

**Design:** `issue-449-visible-fit-failure-policy-design-2026-09-25.md`.
**Implementation plan:**
`issue-449-visible-fit-failure-implementation-plan-2026-09-25.md`.
**Prior slice reviews:** I449-3 and I449-4, including the annotation and
axis-overflow corrections.

## Decision

Accepted.  I449-5 closes the visible-fit release gate.  No normal fit or
placement condition chooses refusal as its outcome.  Layout completes the
geometry, completed canvas, and typed `FitWarning`; Scene serializes those
facts; every target consumes that supplied canvas.  Invalid input, resource
closure, identity, and target-serialization errors remain outside this policy.

This supersedes the unimplemented #400 draft/immutable split.  The owner
decision in #449 makes the disposition the same for both paths: a fixed draft
or immutable Context produces a visible artifact and warning.  Consequently,
there is no longer a hidden path-specific refusal default to document or
maintain.

## Acceptance mapping

| Requirement | Released evidence | Result |
| --- | --- | --- |
| A fit/placement failure still produces an artifact | I449-2 transports Layout's completed canvas unchanged to Scene, SVG, PNG, PDF, Typst, and TikZ; the fixed-height row-density integration case has expanded canvas bounds. | Pass |
| The reader can inspect every fallback | `FitWarning` is completed in Layout, required in Scene v0.6, and emitted by the CLI after writing.  Slot/table/row/mark, label/axis, relation, group, network, and annotation families have explicit warnings. | Pass |
| No silent axis loss | Ordinary axis placement completes all intervals; an explicit `thin-with-record` remains the only thinning policy.  The final validator recognizes only explicitly marked `visible-overflow` text overlap. | Pass |
| Dense rows and overflowing marks remain visible | The multi-lane/multi-milestone fixed-height fixture completes with `W_LAYOUT_ROW_DENSITY` and `W_LAYOUT_MARK_OVERFLOW`; no global mark-containment invariant was weakened. | Pass |
| Explicit degradation remains author-owned | Ellipsis, clipping, wrapping, thinning, and declared suppression remain explicit.  `diagnose` has no live fit/placement reader and `suppress` is not a default. | Pass |
| Scene and adapters do not make policy | Layout owns candidate selection, routes, warning records, and canvas completion.  Scene primitive-delivery and import-direction gates pass on all supported platforms. | Pass |

## Public artifact review

The full committed corpus was regenerated through the public materializer.
Scene resource-closure identities changed where the expanded font closure is
declared.  The visible SVG changes are attributable to the released typed
numeric treatment, the selected monospace briefing role, and completed
placement geometry; the `halcyon-1/replan-baseline` artifact now retains its
previously rejected axis labels as explicit visible-overflow placements.  The
public reproduction suite verifies that every committed Scene/SVG pair is the
deterministic result of its declared Context.

## Verification

- Focused release evidence:
  `test_declared_examples_reproduce_by_public_cli`, packaged-resource,
  font-metric, and surface-quality tests: **30 passed**.
- `git diff --check` passes for the released source and generated corpus.
- GitHub Actions run `36159854167` passed on Ubuntu, macOS, and Windows:
  conformance, documented commands, structural/reachability/coverage gates,
  full `pytest -n 4`, primary-wheel size enforcement, and installed-wheel
  smoke.
- The same run's Python 3.12 reproduction job passed every public
  materializer Context.

## Architecture result

The authority chain remains Project/View and Theme intent → Layout completion
→ Scene projection → target serialization.  The release introduces neither a
renderer fallback nor a compatibility reader for the retired refusal policy.
The #400 concern is therefore resolved by the broader #449 decision, and both
issues are ready to close.
