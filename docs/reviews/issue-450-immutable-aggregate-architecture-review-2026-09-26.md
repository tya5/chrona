# Architecture Review — Immutable Aggregate Diagnostics (#450)

**Decision:** Accepted.

The correction preserves the one-way ingress → typed closure boundary.  The
collector remains validation-only, resource-set discovery remains at Context
and preset envelopes, and neither Layout nor Scene observes invalid input.
Using the existing CLI diagnostics transport avoids a parallel error protocol.
