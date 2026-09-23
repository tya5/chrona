# #257, #308, and #258 Acceptance-Evidence Correction Implementation Plan

**Design prerequisite:** [accepted correction](../../reviews/current/issues-257-308-258-acceptance-evidence-design-correction-2026-09-23.md)

## C1 — #257 public analysis proof

Extract the successful schedule payload into one pure CLI helper.  Add CLI
tests for Project insertion-order critical IDs, HALCYON analysis facts, and a
rejected schedule payload that has diagnostics but no `analysis` member.

## C2 — #308 source and omission proof

Add Draft-pipeline integration tests for an actual-progress fill, a zero or
absent progress source, and a missing corresponding host.  Assert emitted
semantic IDs/purpose for success and absence of a fill for optional cases.

## C3 — #258 complete Draft CLI proof

Add CLI tests for a partial descriptor, guided Draft descriptor rejection, and
guided TikZ source output with a complete descriptor.  Preserve the existing
explicit Typst source and Context schema rejection tests.

## C4 — Acceptance gate

Run focused tests, full pytest, conformance, all eight public materializers
with a generated-SVG diff, and an isolated installed-wheel smoke.  Amend each
acceptance review with the correction evidence and reclose each Issue.
