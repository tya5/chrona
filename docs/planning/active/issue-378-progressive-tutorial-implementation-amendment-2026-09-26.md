# Implementation Amendment — Progressive Tutorial (#378 I378-3)

**Design:** `issue-378-progressive-tutorial-boundary-correction-2026-09-26.md`.
**Architecture review:**
`issue-378-progressive-tutorial-boundary-architecture-review-2026-09-26.md`.

## T378-3A — Small independent Draft fixtures

Add seven complete, independently renderable Project YAML files under one
`examples/onboarding/` source directory. The sequence introduces spans,
gates, relations/lag, calendars, constraints/deadlines, hierarchy/rollup,
then Actuals/progress. Include an Actual Set only for the last stage. Avoid
copying large corpus sources. Acceptance: each fixture passes the Project
contract and Draft render; an edit to a task title changes its SVG; the final
stage shows observed progress.

## T378-3B — Executable guide and advanced sources

Document one command per Draft fixture, then explicit public materializer
commands for the HALCYON scenario and snapshot slides and ORION extension
slide. Link the exact owning Project, View, Context, snapshot-ref, and package
sources for each advanced concept. Verify the View actually selects the
scenario/snapshot and the extension is in the immutable closure. Update the
first-project guide to lead into this tutorial. Acceptance: the documented
command gate executes each command in a disposable workspace, and advanced
slides reproduce committed bytes.

## T378-3C — Literal acceptance and publication

Run focused fixtures/render tests, batch generated-document refresh, public
materializer reproduction, conformance, wheel smoke, and SVG impact review.
Publish an English #378 acceptance review mapping all six rungs and their
commands/artifacts. Observe one final CI run, then close #378 only when the
literal acceptance matrix is green. #454 remains the reviewer priority board.

Each slice is independently reviewable; no implementation may substitute a
successful generic render for proof of a selected scenario or snapshot.
