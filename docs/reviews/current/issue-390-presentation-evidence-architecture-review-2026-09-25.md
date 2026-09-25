# Architecture Review: Presentation evidence and inspection boundary (#390)

**Decision:** Accepted for implementation planning.

The all-Scene delivery check preserves the Scene boundary: serialized
inspection facts are legitimate consumers and need not be duplicated in SVG.
The finite ownership manifest prevents both dropped metadata and invisible
allowlisting.  The prior-art matrix consumes #391's declared ceiling only and
therefore cannot introduce a second vocabulary or product roadmap.  The visual
acceptance record supplements deterministic generated evidence but has no
runtime authority.  These boundaries align with Specifications 12, 32, 55,
58, and 63.
