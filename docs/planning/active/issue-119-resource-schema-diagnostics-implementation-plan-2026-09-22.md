# Issue 119 — Resource Schema Diagnostics Implementation Plan

## I119-1: Structured schema failure

- Add a `SchemaContractError` carrying resource kind and JSON pointer.
- Select the deterministic first `Draft202012Validator` error and convert its
  absolute path to an escaped JSON pointer (`/body/tableColumns/2/source`).
- Keep unknown kind/version as the existing generic closure-kind error.

## I119-2: Closure and CLI propagation

- Extend `ClosureError` with `source_ref`.
- Map schema failures in `_load_reference` to a stable per-kind code and retain
  the pointer through the CLI failure adapter.
- Do not change identity, snapshot, or renderer diagnostics.

## I119-3: Verification and publication

- Add parameterized negative closure tests for View, Theme, Color Scheme,
  Actual set, and Summary profile; assert both code and pointer.
- Run focused closure/CLI tests, full pytest, public materializers, import and
  reachability checks, then publish one implementation PR.
