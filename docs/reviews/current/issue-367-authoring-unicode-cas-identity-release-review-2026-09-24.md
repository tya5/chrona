# Issue 367 release review

`content_identity` is now the sole authoring workspace revision codec. The
command base revision, candidate closure identity, and CAS writer therefore
agree for Unicode content. A Japanese workspace title updates successfully at
its current revision; stale revisions retain `E_AUTHORING_BASE_REVISION`.

Focused authoring/materialization/CLI tests: 51 passed. Three-OS CI remains the
release gate.
