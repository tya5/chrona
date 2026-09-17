# Use Case Design Readiness Review

**Status:** Review complete  
**Scope:** UC-01 through UC-13 in [14 Use Case Catalog](14-use-case-catalog.md).

## Conclusion

Core planning, Git review, plan-versus-Actual, expressive annotations, independent
Views, Actual reconciliation, baseline capture, and declared target capability now have
an owning specification and at least one structural fixture. No reviewed use case
requires a change to Core semantics, resource/cost management, or renderer-authoritative
state.

## Design-ready versus implementation-ready

| State | Use cases | Next gate |
|---|---|---|
| Design-ready | UC-01, UC-02, UC-03, UC-05, UC-08, UC-09, UC-10, UC-12, UC-13 | semantic conformance runner |
| Design-ready with adapter deferred | UC-04, UC-06, UC-11 | exporter, AI, CLI/CI adapters |
| Design needs extension fixture | UC-07 | package schema and semiconductor profile fixture |

## Remaining design constraints

- An explanatory arrow must remain distinct from a dependency in all command, Scene,
  and target-capability tests.
- A multi-context runner must prove no Context reads another Context's View, Theme,
  Actual, viewport, or cache state.
- Actual resolution and Snapshot capture require semantic runner checks for immutable
  revision and stable-ID validity before any adapter claims support.

The next planned work is conformance-runner design and implementation. It must consume
the existing manifest and fixtures before interactive or exporter implementation begins.
