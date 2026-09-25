# Architecture Review — Completed-Canvas Acceptance Correction (#449)

**Decision:** accept.

The correction aligns the output test with the published artifact contract
without adding a second geometry authority.  It preserves the architectural
flow:

```text
Context minimum viewport -> Layout completed canvas -> Scene -> SVG root canvas
                                                         -> output-property test
```

Using the SVG root boundary is appropriate for a serializer-level property:
the test sees exactly what a user sees.  Requiring root/viewBox coherence and
the Context lower bound prevents the test from weakening into an arbitrary
larger-document exemption.  There is no migration, compatibility layer,
renderer reflow, Scene special case, or corpus-specific allowlist.

The design is consistent with #449's invariant that visible fallback geometry
may cross former allocations but never the completed canvas, and with the
existing Layout → Scene → adapter responsibility split.  Proceed with the
narrow test correction only.
