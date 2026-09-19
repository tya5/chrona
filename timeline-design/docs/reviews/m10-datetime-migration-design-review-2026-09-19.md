# M10 DateTime Migration Design Review — 2026-09-19

**Disposition:** Pass — M10-3 is authorized after publication.

The prior provenance field did not define the conversion policy sufficiently to produce
reproducible DateTime values. It is now a structured non-midnight zone/time/DST policy.
The migration subset and all rejection cases are explicit, conversion is all-or-nothing,
and every `timeline/v0.2` document rejects downgrade to Date-only v0.1. This preserves
the original Project and prevents an adapter from silently dropping semantics.
