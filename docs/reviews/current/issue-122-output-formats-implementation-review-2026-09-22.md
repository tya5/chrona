# Issue 122 — Output Formats Implementation Review

## Decision

Accept the output-target implementation.  `render` and `render-review` now
enter one completed-review pipeline and emit an opaque typed artifact selected
by the v0.7 Context target.  SVG remains byte-identical; PNG and PDF are
optional presentation adapters, never alternate geometry engines.

## Boundary review

- Core exposes only `RenderArtifact` and the Renderer protocol.
- Presentation closure validates the v0.7 target/environment declaration;
  registry/adapters own format and backend checks.
- Layout and Scene remain target-neutral and receive no format/backend input.
- CLI parses/asserts format and writes bytes; immutable `--format` cannot
  override a Context target.
- PNG uses verified CairoSVG/Cairo/DPI.  PDF uses verified svglib/ReportLab
  with ReportLab invariant mode, after CairoSVG PDF was measured non-deterministic.

No v0.6 resolver/schema path, generic renderer fallback, host-default backend,
or lossy required capability path remains reachable.

## Verification evidence

- Target registry tests cover PNG/PDF signatures, repeated bytes, semantic
  capability rejection, and backend identity mismatch.
- CLI tests cover draft PNG/PDF output and immutable format mismatch with no
  output artifact.
- Existing SVG review, closure, materializer, and pipeline tests retain exact
  generated SVG bytes.
- Complete pytest, conformance, import/reachability checks, and five public SVG
  materializer checks are rerun before publication; no generated SVG is updated.
