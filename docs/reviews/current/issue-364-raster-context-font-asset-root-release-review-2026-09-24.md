# Issue #364 — Raster Context-Font Asset Root Release Review

## Decision

Accept #364. Public commit `005a725` removes CLI-owned default adapter
construction. `render_review` now passes its single resolved effective asset
root to both metric resolution and the default adapter construction path.

## Evidence

- The public CLI imports a local font descriptor and successfully renders PNG
  and PDF; the importer-created byte pair remains beside the descriptor.
- The materializer copies a Context-relative font pair into a snapshot,
  rewrites its locator, and a default PNG adapter resolves that copied file.
  The artifact adapter identity includes the verified font identity.
- Existing package-provider CJK SVG/PNG/PDF coverage remains green, as do
  metrics-only SVG and missing-byte rejection tests.
- Local conformance and public corpus inventory pass.
- GitHub Actions run
  [35965145241](https://github.com/tya5/chrona/actions/runs/35965145241)
  passed on Ubuntu, macOS, and Windows, including structural gates, full
  parallel pytest, wheel build/install, and isolated smoke tests.

## Architecture conclusion

The fix introduces no renderer-side Context discovery and no new font policy.
The application render use case remains the only normal place that resolves
the closure asset root; Layout consumes pinned metrics and raster adapters
consume verified byte files after completed Scene construction. Explicitly
injected renderers remain a host/test seam only.
