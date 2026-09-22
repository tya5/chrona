# Issue 122 — PNG Backend Design Correction

## Evidence

CI installed the declared CairoSVG extra on both operating systems.  Ubuntu
loaded Cairo, but macOS failed before rendering because CairoSVG/cairocffi also
requires an externally installed native `libcairo`.  Thus the declared Python
extra was not a complete optional renderer dependency and draft rendering could
not be validated consistently across supported CI platforms.

## Corrected decision

PNG uses `resvg-py` instead of CairoSVG.  Its wheel contains the Rust resvg
engine, exposes a stable Python package version and resvg engine version, and
does not require a host graphics library.  The PNG descriptor is:

```yaml
rasterizer:
  engine: resvg-py
  version: 0.5.0
  resvgVersion: 0.48.1
  dpi: 96
```

The renderer verifies both versions and DPI before conversion.  PDF remains the
previously corrected invariant svglib/ReportLab adapter.  Both renderers remain
optional `render` extra dependencies and report `E_RENDER_RASTERIZER_UNAVAILABLE`
when missing; neither asks users or CI to install an unrecorded system library.

## Scope

This replaces only the PNG serialization adapter and its Context identity.  It
does not alter the typed Renderer contract, target capability policy, completed
Scene handoff, CLI selection, or the PDF correction.
