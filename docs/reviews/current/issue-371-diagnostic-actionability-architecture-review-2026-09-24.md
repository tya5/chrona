# Issue #371 — Diagnostic Actionability Architecture Review

**Decision:** Accepted for implementation planning

The proposed disposition model replaces #370's generic grandfathering without
weakening its exact-population gate.  Import-graph reachability is the correct
public-boundary fact: it includes projection failures that a public command can
emit while excluding repository tools.  Detail is added where facts originate,
so CLI, Layout, Scene, and renderers do not become diagnostic translators.

The policy is still conformance-only and the `baseRevision` correction retains
the optimistic-concurrency assertion rather than treating it as hidden product
bookkeeping.  No unresolved authority, compatibility, or presentation-boundary
issue remains.
