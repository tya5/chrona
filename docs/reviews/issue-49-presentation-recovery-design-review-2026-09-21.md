# Issue #49 cross-boundary design review

## Boundary review

- Project/Actual provide temporal facts; View makes presentation selections.
- Detail owns legend entries; Layout supplies slots and measurement constraints.
- Theme supplies metric and semantic role values only.
- Scene consumes normalized facts and measured placement, never source IDs or example names.
- CLI validates before rendering; materializer derives and verifies immutable example closures.

## Decision

The recovery is approved as one plan with independent implementation slices. Each slice adds focused evidence before the next; generated SVG regeneration is last because it is derived evidence, not a source fix.