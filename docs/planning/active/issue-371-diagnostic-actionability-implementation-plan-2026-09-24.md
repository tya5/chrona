# Implementation Plan: Diagnostic Actionability (#371)

**Status:** Complete

**Implements:** [Issue #371 design](../../design/issue-371-diagnostic-actionability-design-2026-09-24.md)

## I371-1 — Disposition-aware inventory

Migrate every policy entry to `sufficient` or `backlog`; validate required
reason/next-action fields and render backlog code/site-count/action rows.
Add focused policy/generator negative tests and regenerate the inventory.

**Acceptance:** no reason-only entry is accepted; missing/unknown/stale
dispositions fail deterministically.

## I371-2 — Public reachability classification

Extract/reuse import-graph discovery for CLI roots in the diagnostic tool.
Add regression tests for a reachable presentation module and an unreachable
module; disposition `E_ACTUAL_REQUIRED` correctly.

**Acceptance:** source location alone cannot determine user-facing status.

## I371-3 — Owner-local high-volume details

Implement detail helpers and focused tests for every selected
`E_CLOSURE_KIND`, `E_STORE_REFERENCE`, and `E_MATERIALIZER_CONTEXT` construction.
Regenerate policy/inventory and verify no bare selected code remains unless an
explicitly justified distinct site is backlog.

**Acceptance:** each failure exposes resource/reference, expected value, and
found/absent value through its existing product boundary.

## I371-4 — Identity correction and release

Change `baseRevision` policy classification to `pinned-deliberately` with its
producer.  Run focused tests, full pytest, conformance and all quality gates,
public materializer byte checks, wheel smoke, generated-report review, and
Ubuntu/macOS/Windows CI. Publish a release review before closing #371.
