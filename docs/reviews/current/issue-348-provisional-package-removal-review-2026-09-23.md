# #348 Provisional Package Removal Review

**Date:** 2026-09-23  
**Scope:** removal of provisional Summary, package, lock, acquisition, and CLI code
**Decision:** Accepted

The #348 correction requires corpus evidence before package machinery. The
provisional implementation had no committed preset, reusable corpus source,
materializer store boundary, or guided consumer; retaining it would create an
unsupported public authority. It is therefore removed completely, including
schemas, schema inventory entries, CLI command, unit fixtures, and inspection
tooling.

The removal does not change Context resolution, Layout, Scene, renderers,
materializers, or existing authoring commands. CLI regression and schema/
example inventory gates pass. Package design remains Specification 62 deferred
work, with a new implementation only after C-GDF-1 through C-GDF-3 establish
actual content and evidence.
