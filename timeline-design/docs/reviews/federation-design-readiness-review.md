# Federation Design Readiness Review

**Status:** Conditionally complete — full conformance requires CI dependency environment  
**Scope:** UC-14, Federation Plan/export/command contracts, and Render Context v0.2.

## Result

The Federation design has one authority boundary at every layer: child Project/export,
parent Federation Plan, Render Context selection, derived View/Scene projection, and
parent-only Federation Commands. No document grants a parent mutation authority over a
child Project or makes a child branch tip an evaluation input.

## Review evidence

| Concern | Result | Evidence |
|---|---|---|
| Independent ownership | Pass | Separate child export and parent Plan resources; Commands target only the Plan. |
| Reproducible selection | Pass | Repository locator, full Git revision, and content identity are declared. |
| No implicit child update | Pass | Before/after repin closure fixtures expose both child revisions and select only the Plan-pinned revision. |
| Presentation boundary | Pass | Federated items are read-only View inputs; child progress is not a scheduling input. |
| v0.1 compatibility | Pass | Federation is opt-in through Render Context v0.2; v0.1 schema remains unchanged. |
| v0.2 structural parity | Fixed during review | Viewport and typed input/reference constraints were restored to v0.1-equivalent requirements. |

## Verification status

`git diff --check` and Python fixture-runner syntax compilation pass locally. The full
conformance runner requires the declared `jsonschema` dependency, which is unavailable
in this execution environment. CI must run the full runner before any implementation
readiness claim.

## Remaining implementation boundary

This is a design-complete contract, not a remote Git resolver, exporter, GUI, or
renderer implementation. A future resolver must enforce the documented trust policy
against real repositories and emit the specified diagnostics.
