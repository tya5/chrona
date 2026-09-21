# M27 I27-R3B2 Optional Family Review — 2026-09-21

**Decision:** Complete after regression/conformance verification and publication.

The v0.5 path resolves Detail Profile data against the immutable Layout Manifest,
then materializes group details, milestone digests, summary panels, and selected View
annotations only into their matching optional slots. Annotation geometry is bounded by
the resolved slot; no free coordinates, raw Settings input, or legacy Theme shape is
used.

**Evidence:** full regression (196 passed) and conformance.
