# ORION ASIC example

The **extension** register of the corpus: a project whose object types and typed fields
come from a declared profile package rather than from Chrona's core vocabulary.

- `project.yaml` declares `extensions[0].resource`, a pinned reference to
  `extensions/semiconductor-development.yaml`, a `chrona/profile/v0.3` package that
  defines the `EVT`, `DVT` and `PVT` gate profiles, the `approval` enum field they
  require, and the package-wide `revision`, `customerReview` and `lot` fields.
  The package's own `contentIdentity` frames the document with that field omitted; the
  project's reference pins the exact file bytes, which the closure verifies.
- Objects use the package types directly (`type: EVT`) and carry its fields. Every
  object has a `revision`; `views/gates.yaml` encodes it as a colour scale
  (`colorEncoding` over `A0`, `A1`, `B0`), with the named slots supplied by
  `schemes/orion-light.yaml` and the mapping by `themes/orion-light.yaml`.
- `actual.yaml` records a point observation for each gate that has been held, an
  in-flight observation with partial progress, and one unmatched supplier record.
- `dvt-pvt` carries a negative lag: production validation is fast-tracked to start
  three working weeks before design validation closes.
- `contexts/gates.yaml` is the immutable binding; `generated/gates.svg` is the
  materializer evidence declared by `manifest.yaml`.

The draft `chrona render` path does not resolve extension packages, so the package
is exercised only through the materializer and `render-review` closure, where the
declared package must be read (`--reject-unused-closure-inputs` proves it).
