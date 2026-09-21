# Issue #50 closure-integrity implementation plan

## Preconditions

- Issue #50 execution record reviewed.
- PR #51 evidence-only refresh merged.
- `50-materializer-closure-integrity.md` and its design review published.
- No legacy Settings/Theme contract may be restored.

## I50-1 — Preserve and validate authored closures

1. Refactor `tools/materialize_example.py` so reference copying does not mutate input
   dictionaries.
2. Copy authored context bytes without YAML re-serialization.
3. Validate direct and nested reference pins and declared font asset pins before CLI render.
4. Emit derived provenance separately, if retained.
5. Add positive byte-preservation and negative stale-pin tests.

## I50-2 — Repair #49 residual test contracts

1. Make required title measurement lookup use
   `E_PRESENTATION_MEASUREMENTS_REQUIRED`.
2. Update v0.5 builder fixtures to provide their required title measurement.
3. Correct the baseline-capture test to assert the flat snapshot-reference shape.
4. Refresh the three stale HALCYON authored `actual` pins only after calculating their
   exact current source digests.

## I50-3 — Evidence and regression closure

1. Run focused Scene, snapshot, materializer, and exact-source-byte tests.
2. Run all manifest contexts in check mode; they must be byte-identical after PR #51.
3. Run the full pytest suite and classify any remaining failure by owner.
4. Record exact commit, commands, pass/fail count, closure-negative result, and unchanged/
   regenerated evidence in Issue #49/#50.
5. Close #49 only if all listed recovery outcomes are green; otherwise open a narrowly
   owned follow-up issue.

## Commit and publication discipline

Publish I50-1, I50-2, and I50-3 as separate reviewable commits. For each phase, update
`main` only through the GitHub integration after confirming its current head SHA.
