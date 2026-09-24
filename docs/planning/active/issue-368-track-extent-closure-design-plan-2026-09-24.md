# Issue 368: completed track extent closure design plan

## Correction

The initial #368 change added a `3 * markSize` lower bound beside the completed
track placer. Although derived from one current offset rule, it duplicates the
rule and can drift when lane, milestone, planned/actual, or folded-point
placement changes. It is not an acceptable lasting design.

## Required design

One Layout-owned track planner must expose both completed placements and the
minimum block extent that contains them. `timeline_content_block_requirement`,
fixed-overflow diagnostics, and Draft auto extent must consume that same
planner result. Scene must continue to receive placements only.

The planner must cover shared and stacked lanes, planned/actual companions,
point milestones, and every current row source kind. Group-header folded points
remain a distinct header allocation with its own declared diagnostic.

## Gates

Create public synthetic multi-lane/multi-milestone cases, prove auto resolves
their finite extent, prove one-pixel-less fixed viewports reject with an
actionable Layout diagnostic, remove the duplicated multiplier, and complete
architecture/release review before publication.
