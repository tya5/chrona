# Implementation Plan: Historical lane helper reachability correction (#385)

**Status:** Accepted.

**Implements:** [Lane reachability correction](../../design/issue-385-lane-reachability-correction-2026-09-25.md)

## R385-1 — Remove the abandoned parallel policy

Delete `src/chrona/presentation/layout/lanes.py` and
`tests/unit/chrona/presentation/layout/test_presentation_lanes.py`.

**Acceptance:** no product or test import remains; no staged-module entry is
introduced; focused `surface_quality` and presentation Layout tests pass.

## R385-2 — Re-run the release boundary

Run module reachability, import direction, conformance, full pytest, and the
existing I385-3 public materializer and generated-artifact checks.

**Acceptance:** the correction changes no checked-in Scene or SVG artifact
bytes and every I385-3 gate is green.
