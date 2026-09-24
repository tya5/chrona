# Architecture Review: Presentation vocabulary coverage (#375)

**Decision:** Approved.

The proposed boundary is structurally aligned with Chrona's architecture.
The coverage tool is a reader of public schemas, declared Context closure, and
serialized Scene artifacts; it neither controls presentation decisions nor
recreates them.  The Scene v0.2 correction is necessary because an allocated
slot is not evidence that it produced a primitive.  Carrying the relation from
Layout placement through Scene is the only design that avoids geometry and
purpose inference.

The review rejects three alternatives:

* parse committed SVG `data-purpose` values — target-specific and insufficient
  to identify a Layout slot;
* map primitive purpose strings to slots in the tool — a duplicate Scene
  builder policy that will drift;
* report only declared Layout slots — it cannot select work that requires
  output evidence, including #382's overlay model.

The report remains explicitly non-gating.  It names the next curation work but
does not make breadth a correctness requirement for an individual render.
