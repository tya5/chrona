# M26 Operational Workflows Implementation Plan — 2026-09-21

**Status:** Approved implementation plan.  
**Design inputs:** Specification `35`, ADR-0024–0026, M26 CLI/CI release design, and
the M26 design review. No step may alter those contracts without a design amendment and
new review.

## Delivery order

| Slice | Scope | Required automated evidence | Publish boundary |
|---|---|---|---|
| I26-1 | resource codecs and schema registration for intake batch, command v0.2, automation result, snapshot v0.2 | positive schema fixtures; malformed/unknown fields; canonical identity serialization | schemas/codecs/tests |
| I26-2 | provider-neutral immutable reference verifier and durable command replay ledger | wrong ID/kind/revision/digest; same-ID replay; changed-ID collision; no working-tree fallback | storage/command tests |
| I26-3 | Actual intake apply and explicit reconcile on CAS Actual Store | inserted/no-op/conflict records; exact ID versus unmatched; atomic batch rejection; Project/schedule isolation | domain/command tests |
| I26-4 | append-only baseline registry and capture command | stale Project; duplicate ID; registry failure; exact snapshot reference contents | storage/command tests |
| I26-5 | baseline comparison service and machine result construction | verified baseline/candidate; cross-store positive/negative; deterministic comparison closure | integration tests |
| I26-6 | CLI commands, atomic `--result`, exit mapping, and `propose-set` removal | A26-01 through A26-10; no existing output overwrite; secret redaction; no checkout CI | CLI/acceptance tests |
| I26-7 | conformance registration, documentation surface, final review, and release claim | full test suite; conformance; acceptance matrix; docs/catalog/ledger consistency | final acceptance review |

**Progress:** I26-1 through I26-5 completed and published on 2026-09-21. The Actual-set
v0.2 provenance amendment, append-only registry, and verified semantic baseline
comparison all have automated evidence. I26-6 is in progress: `baseline-compare` now
uses Store-config v0.1 and atomic result output; command check/apply, intake, resolve,
capture, and legacy `propose-set` removal remain in this slice.

## Implementation rules

1. Implement slices in order. Publish every completed slice to `main` before starting
   the next one.
2. Add failing tests for the slice's required evidence before or alongside its code.
3. Do not modify scheduler, renderer, Project format, View format, or legacy v0.1
   behavior except the planned removal of the `propose-set` CLI surface in I26-6.
4. A Store adapter, result writer, or replay ledger that cannot meet its atomicity rule
   is a design stop: amend Specification `35` and repeat the design review.
5. Keep legacy v0.1 parser support isolated. Do not silently up-convert a raw path into
   a v0.2 immutable reference.

## Completion gate

M26 is complete only when all I26 slices are published, all A26 acceptance cases pass,
UC-10/11/12 product-surface rows name the new commands, and the final review confirms
the exact released behavior. Until then the use-case catalog continues to report these
as designed but not product-exposed.
