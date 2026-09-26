# Implementation Amendment — Fit Specification Supersession (#457)

**Design:** [specification supersession](../../design/issue-457-fit-specification-supersession-2026-09-26.md) and [architecture review](../../reviews/current/issue-457-fit-specification-architecture-review-2026-09-26.md).

Before L2 acceptance, delete the now-dead `E_LAYOUT_REQUIRED_OVERFLOW`
immutable rematerialization rewrite in `usecases/render_review.py`. Keep the
normal `SceneBuildError` translation, because invalid resource/placement
diagnostics still need a presentation boundary. Add a structural assertion
that no production Layout site raises the retired fit error, and test that
valid narrow immutable rendering succeeds without a rematerialization hint.

Regenerate `docs/diagnostics/inventory.md` with the source change. Review the
L2 raise-site audit against all five corrected living specifications; if an
additional valid-fit refusal appears, return to design. Publish this code
with the L2 geometry changes as one coherent implementation slice, then use
the final CI matrix and public materializer byte checks for release acceptance.
