# ADR-0024: Admit external Actuals only as normalized, provenance-bound batches

**Status:** Accepted  
**Date:** 2026-09-21

## Context

External systems report observed work facts, but their APIs, credentials, titles, and
identifiers are not Project authority. A loose importer could silently select a current
Project tip, create duplicate observations on retry, or title-match the wrong object.

## Decision

Chrona accepts only a self-contained `actual-intake-batch/v0.1` produced by an
adapter. The batch carries a source system, normalized source content identity, and
stable external key per record. Apply is a v0.2 CAS command against one immutable
Actual-set v0.2 reference. The v0.2 observation stores its source content identity so
the required replay/conflict check remains auditable. `(source.system, externalKey)`
is the deduplication key.

Exact Project IDs may be carried by a record and are checked against an explicit
immutable Project reference. All other observations remain explicitly unmatched.
Replaying identical fields from the same source identity is a no-op; differing facts
are rejected for explicit edit/reconciliation. No connector, title, or URL may select
or mutate a Project.

## Consequences

- Initial integrations normalize data outside the core; connector implementation and
  credential policy can evolve independently.
- Operators receive a visible unmatched queue instead of unreliable automatic joins.
- An importer cannot correct an upstream fact by replaying it; the correction has a
  separate audited command.
