# Issue 99 Step 5 — Renderer and Scheduler Protocol Design

**Status:** Proposed design.  **Predecessor:** typed closure Step 4 completed
by PR #139.

## Decision

Introduce two narrow structural protocols in `core.ports`:

- `Renderer`: consumes a completed `SceneSurface`, viewport, and token view,
  returning serialized output.  The existing v0.5 SVG function is adapted by a
  small callable adapter; renderer implementations never receive a closure,
  resource, layout profile, or scheduler result.
- `Scheduler`: consumes semantic Project facts plus extension diagnostics and
  returns a protocol-owned immutable `ScheduleOutcome` (placements and
  diagnostics).  The reference scheduler adapts its existing result to this
  outcome.  The protocol is not named after `datetime_scheduler` and does not
  preserve a staged/deleted implementation as an authority.

The use case receives these dependencies explicitly with the existing reference
implementations as defaults.  CLI remains an adapter and does not select an
algorithm.  Direct non-render CLI/core commands can continue using the
reference scheduler until separately migrated; this step changes only the
review-render use case dependency boundary.

## Ownership review

| Layer | Responsibility after Step 5 |
| --- | --- |
| core ports | declares behavior/result shape, no scheduling or SVG implementation |
| scheduling | reference algorithm adapter |
| presentation renderer | SVG serialization adapter |
| use case | selects injected ports and translates outcome to existing stable diagnostics |
| Layout / Scene | unchanged; SceneSurface remains the renderer seam |

## Acceptance

- `render_review` imports ports, not `scheduling.scheduler.schedule` or
  `presentation.renderers.v05_svg.render_v05_svg`.
- A test fake Scheduler and Renderer prove the use case uses the protocol
  boundary without subprocesses.
- Structural source tests forbid concrete scheduler/renderer imports in the
  render use case.
- Existing default path produces identical diagnostics, read inputs, and all
  public SVG bytes.  No new output format or scheduler policy is introduced.

## Publication

Publish this design/review, then an implementation plan and one implementation
PR.  Step 6 documentation is reviewed against these final boundaries.
