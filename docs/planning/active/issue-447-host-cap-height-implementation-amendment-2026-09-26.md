# Implementation Amendment — Draft Host Cap Height (#447)

After the [design correction](../../design/issue-447-host-cap-height-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-447-host-cap-height-architecture-review-2026-09-26.md) are published, repair H1 in `presentation/fonts/importer.py` and its font tests. Add a Draft-only outline-derived cap-height path for exact host faces; keep declared import strict. Test a real-like missing-OS/2-cap face, absent `H`, and unchanged declared import behavior. The real Ubuntu `fc-match` 400/700 test must complete metrics creation.

Regenerate diagnostic inventories after product changes and publish them with
their source. Run focused font tests locally, then let the three-OS CI matrix
and newest-Python public materializer gate prove release readiness. This is a
H1 correction under the [implementation plan](issues-457-447-fit-and-host-font-implementation-plan-2026-09-26.md), not an extra host fallback or a change to #457's fit policy.
