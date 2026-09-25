# Mark composition acceptance review (#398, #396, #397, #399)

## Scope and evidence base

This review accepts Program B of the published design plan and its mark
composition design, Scene-order correction, and open-terminal correction.
The released implementation is `ecd2ae16` through `9fd2c711`; the final
three-platform release gate is GitHub Actions run `36092322894`.

The final local gates were:

* focused Layout, Scene, SVG, render, and materializer tests;
* public materializer byte checks for all 21 declared corpus slides (24
  materializer integration tests);
* conformance, presentation-coverage, Scene delivery-owner, and generated
  diagnostic/vocabulary inventory checks; and
* full `pytest -n 4`: 792 passed, 19 skipped.

The public CI run repeated conformance, documented command execution,
structural/coverage gates, full parallel pytest, wheel build/budget, and an
installed-wheel smoke test on Ubuntu, macOS, and Windows successfully.

## Acceptance assessment

| Issue | Required outcome | Public evidence | Result |
| --- | --- | --- | --- |
| #398 | Per-role height, offset, corner treatment and paint order; role-derived lane extent; nested comparison marks | Theme v0.8 role geometry, completed `MarkPlacement` geometry, Scene v0.3 `paintOrder`, stable paint/interaction layers, and regenerated comparison corpus scenes | Accepted |
| #396 | Readable mark icon as a badge, with independent contrasting treatment and corpus evidence | `iconMark` resolves an inset host-relative placement and independent paint role; controller-z icon/material-icon slides and coverage exercise the role | Accepted |
| #397 | Rounded host clips partial progress while retaining a square fill stop | completed `clipSourceId`, Scene validation, SVG `clipPath`, unit projection tests, and rounded partial-progress corpus materialization | Accepted |
| #399 | Start-to-as-of open actual, hosted progress, visible open terminal, warning without as-of, and no fabricated missing actual | controller-z `performance` is a `Symbol` open-span from start to as-of; its SVG has the Layout-owned chevron path and matching clip host; render integration proves warning projection and absence of a missing stub | Accepted |

## Boundary and regression review

The final correction exposed two implementation/design mismatches before
acceptance: an `open` field that had no visual shape, and a Layout warning
that was discarded before inspection serialization. Both were corrected at the
proper boundary. Layout now creates the continuation outline and warning;
Scene preserves completed outline/clip/diagnostic data; SVG serializes rather
than derives geometry or policy. The Scene delivery-owner gate explicitly owns
the new diagnostics handoff.

The generated controller-z artifact contains the open actual as a completed
path with a pointed terminal and a `progress-fill` clipped by that exact path.
It is neither a square finished bar nor a missing-actual stub. Source order,
semantic interaction order, and visual paint order remain separately tested.

No compatibility reader was introduced for superseded live Theme, Actual Set,
or View contracts. Historical schemas remain inventory-transition evidence
only. No unresolved design deviation, unowned public Scene field, or
materializer mismatch remains.

## Decision

Program B meets the published acceptance conditions. Close #398, #396, #397,
and #399. Program C (#394 and #395) remains the next independent design and
implementation program.
