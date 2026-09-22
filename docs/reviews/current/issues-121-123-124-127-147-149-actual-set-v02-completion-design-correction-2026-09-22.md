# Actual Set v0.2 Completion Design Correction

`ActualSet.body.asOf` is the immutable observation cutoff consumed by review
projection, not a legacy formatting field.  Actual Set v0.2 therefore accepts
an optional Date-only `asOf`, identical in meaning to v0.1.  An observation
with `externalIdentity` continues to require `sourceContentIdentity`; this is
the provenance that permits an unmatched fact to remain explicit until its
separate resolution command binds it to a Project object.

The migration is atomic: every committed Actual Set becomes v0.2, every
external observation receives its declared content identity, and no parser or
inventory entry accepts v0.1.  This preserves the Core/actual intake boundary,
the immutable Context closure, and View/Layout consumption without granting
renderer or Scene ownership of observation semantics.
