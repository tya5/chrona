# Design Plan — Single Schema Diagnostic Compatibility (#450)

Verify every existing single-diagnostic fixture before replacing explanation
internals.  Separate the legacy wrapper-summary API from the new leaf-list API
so aggregation gains completeness without changing established single-error
messages.
