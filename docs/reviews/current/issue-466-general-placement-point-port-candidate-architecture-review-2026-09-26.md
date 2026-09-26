# Architecture Review — Feasible Point-Port Candidates (#466)

**Reviewed:** [correction](../../design/issue-466-general-placement-point-port-candidate-correction-2026-09-26.md) against Specifications 06, 08, 33, 38, 44 and 50, the common obstacle design, point-port correction and the aster-ssd public Scene.

The finite candidate search is necessary because a point glyph may be overpainted by an independent comparison sibling. A deterministic four-by-four maximum does not introduce unbounded iteration or View/Scene geometry ownership. The same index and route-quality limits decide each pair. Exempting only the selected port preserves the actual/missing-actual sibling collision. Accepted for O2; tests must show the blocked nearest tip is skipped and an alternative route remains visible, as well as stable ordering under unrelated insertion. A route decision and generated Scene/SVG diff must make the selected result inspectable.
