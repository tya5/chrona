# Implementation Plan — Exact Multi-Face Font Measurement (#448)

**Design:** `issue-448-exact-multi-face-font-measurement-design-2026-09-26.md`.
**Architecture review:**
`issue-448-exact-multi-face-font-measurement-architecture-review-2026-09-26.md`.

## I448-1 — Catalog-shaped draft font closure

Replace the one-face `DraftFontResolution` with a deterministic multi-face
closure containing a `FontMetricsCatalog`, sorted exact faces, and matching
`FontFile` tuple. Derive distinct fully bound Theme role pairs once, resolve
each through the exact system resolver, and reject missing/substituted or
duplicate faces before Layout. Thread the catalog to `render_review` and the
complete file tuple to the Draft PNG adapter.

**Files:** `fonts/system.py`, `model/closure.py`, CLI/render request
wiring where it consumes draft resolution, target registry call sites, and
focused closure/system/renderer tests.

**Acceptance:** a regular-plus-bold Theme passes `--system-fonts`; its
weight-400 and weight-700 placements record their separate exact identities;
PNG receives both pinned files with system fallback disabled; a missing 700
face rejects before Layout; no Context or Scene contains a host path.

## I448-2 — Completed corpus identity audit

Add one deterministic checked tool/report that loads each committed immutable
Scene and its declared Context font catalog, checks every text placement
against its completed family/weight/identity, and reports per-weight coverage.
Integrate it with conformance after the existing scene evidence checks. Add
fixtures for an unavailable catalog pair and mismatched identity; regenerate
the public report only after the checker is correct.

**Files:** new focused model/tool tests, new tool and generated diagnostic,
`conformance/run_conformance.py`, diagnostic inventory where required, and
release review.

**Acceptance:** every corpus placement's `assetIdentity` equals the file
declared for its `(family, weight)`; no corpus weight-700 placement carries a
400-face identity; stable failure diagnostics identify the primitive and
expected/actual closure facts; `--check` detects report drift.

## Verification and publication

Run focused unit/integration tests after each slice and `git diff --check`.
At the release gate run the identity audit in check mode, conformance/document
checks, public materializer reproduction, and a generated SVG diff review.
Use one GitHub CI observation after the final material change for the full
three-platform suite; do not duplicate full local pytest or repeatedly poll.
