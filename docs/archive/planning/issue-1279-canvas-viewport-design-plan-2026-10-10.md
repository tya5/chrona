# Issue #1279 — canvas viewport design plan

Published baseline: ready main `5360a127bc8dcee13b1e5ae137475f6c9f12c704`.
Authority: [issue and later acceptance note](https://github.com/tya5/chrona/issues/1279).
Started #918/#927 releases retain merge priority; this diagnostic is independent.

## Literal acceptance

- A test where content needs more than the viewport yields the warning with correct sizes; a fitting surface yields none.
- On current main, the warning appears for exactly the slides whose SVG viewBox differs from their declared viewport (list them in the PR).
- Do not edit `examples/**`.
- Later note: a test with a negative viewBox origin must also yield the warning; auto block has no declared block-size limit.

## Baseline and questions

Published code grows the allocation before Layout completion, then unions completed
geometry into the canvas. Comparing only the adjusted allocation loses the original
declaration. Table-timeline and dependency-network have separate completion paths.
The exact current warning-slide set and contributor records remain unverified.

Design must define original declaration versus allocation, constrained axes, full
extent comparison, deterministic contributor attribution, one-warning identity,
and the Layout → Scene → shared report transport. Geometry and fit policy stay
unchanged; no scheduling, View selection, corpus exceptions or schema migration.

## Publication and evidence

1. Publish this plan; specify the contract and review Specs 08/33/50/66 plus adjacent auto-block/overflow designs.
2. Publish selected design, architecture review and normative Layout rule.
3. Publish implementation slices and exact evidence gates before product code.
4. Verify synthetic overflow/fitting/negative-origin/auto-block and both surfaces;
   compare all declared materializers as one batch, including actual SVG viewBoxes,
   unchanged geometry and warning membership. Require PR and exact-main release CI.
