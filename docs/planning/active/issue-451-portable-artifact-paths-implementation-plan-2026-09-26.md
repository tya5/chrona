# Implementation Plan — Portable Derived-Artifact Paths (#451)

**Design:** `issue-451-portable-artifact-paths-correction-2026-09-26.md`  
**Architecture review:**
`issue-451-portable-artifact-paths-architecture-review-2026-09-26.md`

## I451-PP-1 — Canonicalize at the report boundary

In `tools/derived_artifact_report.py`, retain the resolved relative `Path` for
local use and derive a single `as_posix()` report value.  Substitute that value
in the headline, `unified_diff` labels, and Actions annotation only.

**Acceptance:** no public report field relies on `Path.__str__`.

## I451-PP-2 — Prove platform-neutral reporting

Extend the focused helper fixture to assert the same slash-separated identity
in the headline, diff header, and annotation path.  The fixture must remain
valid on Windows rather than normalize captured output after the fact.

**Acceptance:** focused helper/runner tests and conformance pass locally; one
three-platform CI run proves the full suite and wheel/smoke paths.
