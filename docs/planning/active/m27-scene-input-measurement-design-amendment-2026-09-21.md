# M27 Scene Input Measurement Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R1 implementation correction required.

During the I27-R2 preflight, review found that the I27-R1 `SceneBuildInput` carries
font metrics but omits `MeasuredSources`. That contradicts Specification 37's closed
input boundary and could permit a Scene builder to recalculate text/geometry from an
implicit value. This amendment does not add a resource or restore any legacy
contract: `MeasuredSources` is already the current derived output of Theme v0.2,
FontMetrics, and source normalization.

The input seam MUST carry the immutable `MeasuredSources` object. Scene composition
MUST consume its `metric_values` and source measurements verbatim; it MUST NOT call
`measure_sources`, resolve Theme metrics, or substitute a renderer default. A missing
or non-`MeasuredSources` value diagnoses `E_PRESENTATION_MEASUREMENTS_REQUIRED`.

I27-R1 is therefore reopened only for this closure correction. I27-R2 remains paused
until the revised seam has tests, full regression/conformance evidence, review, and a
separate GitHub publication.
