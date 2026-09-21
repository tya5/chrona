# M27 I27-R1 Measured Input Correction Review — 2026-09-21

**Decision:** Complete after regression/conformance verification and publication.

The corrected `SceneBuildInput` requires the existing immutable `MeasuredSources`
value. It rejects an absent or wrong-type measurement boundary with
`E_PRESENTATION_MEASUREMENTS_REQUIRED`; the later Scene builder can therefore consume
frozen metrics and measurements without recomputation. The Theme v0.2 typed token
boundary remains unchanged and no legacy settings/paint shape is introduced.

**Evidence:** `test_v05_builder.py`, `test_theme_tokens.py`, full regression suite,
and `conformance/run_conformance.py`.
