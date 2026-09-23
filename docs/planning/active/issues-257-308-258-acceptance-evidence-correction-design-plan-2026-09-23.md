# #257, #308, and #258 Acceptance-Evidence Correction Design Plan

## Trigger

The post-completion audit found that three delivered contracts lack some
published acceptance evidence.  The implementation behavior and architectural
boundaries remain valid; this correction closes proof gaps without extending
product scope.

## Scope

1. **#257:** prove public CLI analysis ordering, successful HALCYON analysis,
   and rejection without an analysis payload.  Extract the plan-promised single
   CLI serialization helper if that preserves the current output exactly.
2. **#308:** prove `actual` and `planned` source paths, zero/absent source, and
   absent host omission through the ordinary render pipeline.  Confirm the
   Actual Set v0.2 `actual.progress` location remains the source authority.
3. **#258:** prove partial descriptor rejection and both explicit/guided Draft
   CLI routes.  Retain the shared typed descriptor and Context schema boundary.

## Invariants

No schema, resource version, data model, Layout/Scene/adapter boundary, public
SVG, or immutable Context behavior changes.  Test fixtures are Draft-only or
temporary and do not create a new materializer corpus role.

## Completion criteria

Each missing acceptance condition has a focused, executable regression test;
the affected Issues have updated acceptance reviews; full pytest, conformance,
all public materializer byte checks, and installed-wheel smoke pass before the
Issues are reclosed.
