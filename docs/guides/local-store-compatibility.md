# Local-store compatibility

Local immutable stores use Chrona's portable revision-directory codec.  A local
store created before the 2026-09-24 portable-layout change is unsupported:
re-create the store or re-capture the Project/baseline into a new local store.

Chrona does not search legacy raw-token directories as a fallback.  One encoded
layout is required for portable immutable references, so automatic migration or
a compatibility reader would make stored bytes ambiguous.

This affects only the local filesystem representation of Store-issued opaque
revision tokens.  It does not change Project, Context, Layout, Scene, or
renderer behavior.
