# Implementation Amendment — Store Routing Correction for #376

Amend I376-2 before release: make `ConfiguredStoreReader` select
`LocalBaselineRegistry` only for a `snapshot-ref` whose revision token begins
with `baseline:`; route all other references through `LocalSnapshotReader`.
Add focused coverage for both routes and retain the full initialized-HALCYON
Context resolution assertion.  Do not copy source `snapshots/` into a second
registry namespace, alter Context tokens, or add a mutable-source fallback.
