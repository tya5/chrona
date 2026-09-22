# Issue 119 — Resource Schema Diagnostics Design Review

## Decision

The contract parser already selects a schema from `(kind, version)` and
validates before freezing a contract.  The defect is diagnostic loss:
`_validate` converts every schema error into `E_CLOSURE_KIND`, and closure/CLI
then reports `/`.  Correct the existing ingress boundary rather than adding a
second validator.

## Design

- Introduce a schema-specific contract failure carrying `kind` and the first
  deterministic JSON Schema error pointer.
- `parse_contract` retains generic contract failures for identity/version/type
  boundary errors; only actual schema-shape failures use the new value.
- `_load_reference` maps the value to `ClosureError` with a stable
  `E_<KIND>_SCHEMA` code and the pointer as `source_ref`.
- `ClosureError` exposes `source_ref`; CLI passes it unchanged to the emitted
  diagnostic.
- Validation remains once, before immutable contract construction, for both
  required and optional closure resources.

## Whole-architecture review

This preserves the ingress sequence `bytes → YAML → schema → immutable
contract → use case`.  It keeps raw document shape out of Projection, Layout,
Scene, and renderer modules, and makes #99's typed contract boundary more
useful without coupling it to any target format.  Identity mismatch and
snapshot failures remain separate because they are not schema failures.

## Acceptance

Negative tests cover misspelled keys in View, Theme, Color Scheme, Actual set,
and Summary profile.  Each failure has its resource-kind code and precise
pointer; valid public closures and full tests remain unchanged.
