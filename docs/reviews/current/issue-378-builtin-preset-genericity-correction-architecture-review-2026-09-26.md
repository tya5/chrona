# Architecture Review — Builtin Preset Genericity Correction (#378)

**Decision:** Accepted for implementation.

The correction prevents evidence from becoming accidental selection authority.
View remains the owner of project selection, so a reusable builtin must use an
explicit generic View rather than inherit a corpus Context's object ids.  Theme
and Scheme retain appearance authority; Layout retains geometry; the copy
command only distributes completed ordinary source.  No renderer fallback or
object-id filtering is introduced.
