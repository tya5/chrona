# Architecture Review — Cross-Python Public Evidence Reproduction (#442)

**Decision:** accepted with the deterministic Layout accumulation boundary.

## Evidence reviewed

* #442's measured 3.11/3.12 final-digit Scene divergence and identical
  three-decimal SVG output;
* the live Python 3.11 cross-platform conformance matrix and
  `requires-python >=3.11` declaration;
* every current presentation-layer `sum` call, classified by numeric domain;
* the #412 accepted authority table and its atomic generated-evidence gate.

## Boundary assessment

The proposed `geometry_sum` belongs in Layout.  Table allocation, route
quality, network extents, and completed text/visual advances decide physical
geometry there.  Moving compensated accumulation into Scene would make Scene
recompute Layout policy; doing it in serializers would conceal differing
completed geometry behind output rounding.  Both violate existing authority
boundaries.

Keeping Decimal sums as Decimal preserves exact profile-engine arithmetic;
coercing those to float merely to share a helper would introduce a new loss of
precision.  Keeping integer/count sums is likewise correct: they do not
produce a placement coordinate.  The structural allowlist prevents this
classification from becoming a blanket exemption.

## Release assessment

Regenerating all public evidence is required.  Selectively changing the three
observed slides would leave future drift hidden in another context and would
not prove the corpus-level materializer contract.  A distinct 3.12 Ubuntu job
is proportional: the present three-OS 3.11 matrix retains portability while
the extra job verifies the missing cross-minor invariant without six full
wheel builds.

Recording Python in provenance, accepting per-interpreter files, or rounding
Scene JSON would weaken reproducibility rather than establish it.  The
accepted design correctly rejects all three.

## Cross-issue assessment

#442 is a prerequisite repair for #412, not an orientation-design amendment.
The issues remain separate by responsibility, but their generated corpus has
one atomic publication boundary: #412 changes immutable View/Profile and
Scene v0.5 inputs, while #442 changes their Layout arithmetic.  Publishing
only one regenerated evidence set would be non-materializable.  The combined
release therefore preserves, rather than weakens, #412's atomic migration and
prevents regenerated evidence from reintroducing a Python-minor dependency.

## Review conditions for implementation

The implementation plan must name each audited call site or an approved
module-level classification, add an exact numeric regression reproducing the
historical allocation divergence, regenerate evidence once, and require both
minor-version materializer gates before merge.
