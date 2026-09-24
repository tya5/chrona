# Architecture Review: Overlay corpus evidence (#382)

**Decision:** Approved.

The current grammar and engine already own overlay placement, so an evidence
slide is the correct scope.  Reusing a current HALCYON Context closure isolates
the Layout variable and prevents obsolete PR #272 contracts from becoming a
shadow compatibility path.  The design correctly distinguishes solver evidence
(direct Layout decision assertions) from render evidence (public materializer
SVG/Scene artifacts).

Keeping `programme-at-scale` deferred is also correct: a single fixed corpus
composition does not constitute responsive gallery design.  No authority moves
from Layout into Scene, the gallery, or coverage tooling.
