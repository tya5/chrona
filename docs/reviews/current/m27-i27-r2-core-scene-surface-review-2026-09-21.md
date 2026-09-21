# M27 I27-R2 Core SceneSurface Review — 2026-09-21

**Decision:** Complete after regression/conformance verification and publication.

The v0.5 core builder converts immutable Layout Manifest sources into Scene slots,
derives rows and contiguous groups from projection order, and carries a closed
half-open timeline scale. It consumes frozen font/source measurements to construct
text layouts and selects the most detailed fitting ISO axis, otherwise diagnosing
`E_PRESENTATION_AXIS_OVERFLOW`.

Table cells come only from `SurfaceContentInput`. Planned, Actual, Missing Actual,
and finish-variance primitives are created from the projection without inferring
missing observations. No renderer, raw authoring resource, legacy setting, or
example identity participates in geometry construction.

**Evidence:** `test_v05_builder.py`, full regression suite, and
`conformance/run_conformance.py`.
