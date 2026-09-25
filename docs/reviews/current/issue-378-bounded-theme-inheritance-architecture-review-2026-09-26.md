# Architecture Review — Bounded Theme Inheritance (#378 I378-2)

**Result:** Accepted with View explicitly deferred.

The design preserves the current architecture: ingress owns source decoding and
effective-resource construction; contracts own schema-validated immutable data;
Layout owns geometry; Scene projects completed placements; adapters serialize.
The effective Theme remains a normal ThemeContract, so no downstream layer can
observe or resolve inheritance.

Exact base identity and cycle checks prevent ambient local state from entering
Draft or Context closure.  Restricting replacement to existing whole `values`
and `roles` entries avoids partial structural merges and preserves Theme's
closed vocabulary.  Retaining only effective ordinary Theme identity in the
closure prevents materializer evidence from acquiring an unresolved source
dependency.

The View audit rejects a premature override surface: its fields jointly affect
semantic selection and surface composition.  Deferral is therefore a
structural boundary, not omitted compatibility work.  The proposal neither
uses nor changes guided-authoring governance overrides.
