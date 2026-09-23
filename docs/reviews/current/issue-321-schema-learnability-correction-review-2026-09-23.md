# Issue #321 Completion Correction Architecture Review

**Result:** Accepted for implementation.

The correction keeps diagnostics below every ingress adapter and outside the
successful Core → View → Layout → Scene → renderer path. Explicit optional
identity prevents a malformed resource from being mistaken for a valid closure.
Expanding annotation traversal changes only authoring metadata validation; it
does not alter schema acceptance or rendering. The correction rejects, rather
than revives, legacy schedule syntax.
