# Issue #258 Honest Draft Typeset Targets Architecture Review

**Status:** Accepted  
**Date:** 2026-09-23

## Consistency review

The design reuses the v0.8 `TypesetterIdentity` rather than creating a Draft
target model or adapter-specific options.  It corrects the former host probe,
which made the advertised Draft contract depend on ambient machine state.

It is consistent with the architecture direction of authority:

| Boundary | Responsibility after #258 |
| --- | --- |
| CLI | conditional descriptor grammar, help, and early completeness diagnostic |
| Draft ingress | freezes explicit inputs and creates one non-evidence closure |
| Render Context contract | validates target-to-engine/grammar invariants |
| Layout / Scene | unchanged geometry and semantic-projection authority |
| Typeset adapter | serializes a completed Scene using the declared identity |
| immutable Context | pins reproducible target/environment inputs independently of host state |

The three scalar switches are intentionally not a persisted resource: they are
an invocation-time Draft environment input, analogous to viewport and locale.
Making a separate descriptor document would add a resource kind and lifecycle
without adding closure authority.  The Context remains the only persistent
typesetter contract.

No compatibility path is retained.  The prior implicit host-discovery behavior
is removed atomically with tests that prove executable lookup is absent from
Draft closure construction.  This preserves Specifications 08, 09, 13, and 51,
and the completed #149 positioned-source contract.
