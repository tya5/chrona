# Architecture Review — Independent Decoration Policies (#431)

**Design reviewed:**
`issue-431-decoration-policy-separation-correction-2026-09-26.md`.
**Decision:** Accepted correction before corpus witness migration.

The proposed closed View object removes the existing row/group policy
conflation.  It is preferable to a special witness flag because all consumers
receive the same explicit semantic selection, and only Layout composes its
geometry.  The correction preserves Theme `none`, Scene absence transport, and
the completed-Scene contrast boundary; no renderer or report logic learns View
syntax.
