# Final Architecture and Acceptance Review

## Scope and evidence

The six-issue program is reviewed at the published P6 baseline plus this P7
closure.  The schema inventory contains exactly one live entry for every kind;
the obsolete Actual Set v0.1 schema, parser mapping, examples, and conformance
fixtures have been removed.  Render Context v0.8 is the only accepted Context
version and the inventory names it as live.

Project v0.3 provides the Core hierarchy boundary; View v0.3 owns selected
rows, WBS depth, and subtree presentation; typed presentation contracts carry
the View/profile vocabulary past closure; Layout completes geometry; Scene
projects it; and SVG, PNG, PDF, Typst, and TikZ are adapter-only render paths.
Materialization and initialization use the public closure/store boundary.

## Acceptance trace

| Issue | Accepted outcome |
| --- | --- |
| #124 | exact live-schema inventory, no transition exception or duplicate live kind |
| #147 | typed View/profile/Context vocabulary at the closure boundary |
| #123 | Project v0.3 Date-only hierarchy and validation/scheduling route |
| #127 | View-owned WBS selection, rows, depth, and summary projection |
| #121 | public materialization and non-overwriting initialization services |
| #149 | Context v0.8, positioned completed-Scene Typst/TikZ source adapters |

No compatibility parser remains for superseded Project, View, Render Context,
or Actual Set schemas.  Deferred capabilities remain explicit: native
typesetter text reflow and host-produced typeset output are not immutable
evidence.  The release gate is the complete pytest suite, two-platform CI, the
schema inventory validator, and public materializer/generated-SVG checks.
