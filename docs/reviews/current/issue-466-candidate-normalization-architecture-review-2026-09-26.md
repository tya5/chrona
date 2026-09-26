# Architecture Review — Candidate Normalization Ownership Correction (#466)

**Correction:** [candidate normalization ownership](../../design/issue-466-candidate-normalization-ownership-correction-2026-09-26.md). **Decision:** accepted before C1 code publication.

The Project and View resource contracts are unchanged. The pure v0.22 vocabulary expansion has no font, slot, obstacle, route or Scene dependency, so the presentation model is its narrowest common owner. Review can normalize before Layout without importing Layout implementation, and Layout can consume typed candidate values without importing Review. This aligns [Specification 06](../../specification/06-view-model.md)'s View intent boundary and [Specification 33](../../specification/33-intent-oriented-layout.md)'s geometry authority. Scene and adapters remain unaffected. Existing accepted O2 obstacle and connector behavior is unchanged. No new public compatibility promise or schema change is introduced.

The C1 acceptance gate remains exact public materializer byte identity, focused typed-expansion tests, import-direction/reachability checks and CI. If another product layer begins deriving candidate policy from rung strings, reject C1 and return to design.
