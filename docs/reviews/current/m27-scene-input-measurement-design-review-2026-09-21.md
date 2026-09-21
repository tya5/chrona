# M27 Scene Input Measurement Design Review — 2026-09-21

**Decision:** Amendment approved; I27-R1 correction is authorized and I27-R2 remains paused.

The amendment repairs an implementation-seam omission, not the product architecture.
`MeasuredSources` is an existing current derived value, produced before layout/Scene
composition. Making it mandatory preserves the closed v0.2 Theme, FontMetrics, and
Layout Manifest path; it introduces neither an authoring resource nor a legacy
compatibility contract.

The corrected seam must reject absent/wrong-type measurements and prove that a
subsequent Scene builder consumes the frozen metric values. After that correction is
published with full regression and conformance evidence, I27-R2 may resume.
