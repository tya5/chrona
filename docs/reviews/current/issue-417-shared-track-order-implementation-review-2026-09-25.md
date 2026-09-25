# Implementation Review — Shared-Track Ordering and Summary-Bar Geometry (#417)

**Result:** Accepted for publication.

## Delivered structure

`shared_track_member_key` is the sole source-kind traversal policy.  All four
former literals now consume it: regular Layout mark composition, folded-point
Layout composition, track placement and Scene projection.  Its stable order is
`snapshot`, `scenario`, `primary`, `actual`, with authored source index as the
tie-breaker.  Theme paint order remains independent.

Every shipped Theme binds the existing `summary-bar` role to an explicit
positive `summary-bar-height` token.  Layout resolves that lane-relative value
before emitting the completed summary-bar placement.  Scene and adapters keep
their projection-only responsibility.

## Evidence and gates

- Unit characterization verifies scenario ordering and summary-bar token
  validation/geometry.
- No duplicated ordering map or summary-height division remains in production
  source.
- All 21 public corpus slides were regenerated; the public materializer suite
  reports `24 passed` after byte comparison.
- `pytest -q` reports `811 passed, 19 skipped`.
- Presentation and corpus coverage checks, schema-reference validation, and
  `git diff --check` all pass.

The generated scene provenance changes are expected because the Theme resource
identities now include the explicit summary-bar geometry declaration.
