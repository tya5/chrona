# M28 Review Row Composition Implementation Review

**Status:** Accepted
**Date:** 2026-09-21

## Scope

This review covers the M28 design in Specification 38 and ADR-0029:

- View-owned Review Rows and ordered Review Items;
- explicit primary, snapshot, and actual sources;
- row-level table subject and grouping;
- independently pinned Snapshot Project closure;
- Scene subtracks, instance IDs, annotation ambiguity, and relation expansion; and
- automatic-row migration for the current Executive example.

## Evidence

The following command completed successfully:

```text
PYTHONPATH=src:. python -m pytest -q tests/unit/chrona/presentation/model/test_projection_rows.py tests/unit/chrona/presentation/model/test_snapshot_context_closure.py tests/unit/chrona/presentation/scene/test_v05_builder.py
```

Result: `8 passed`.

## Boundary checks

- No Project, Schedule, Actual, Theme, or Color Scheme resource acquires View row membership.
- Snapshot data remains a pinned immutable resource; no copied schedule payload or latest fallback exists.
- A repeated source/object is identified by row and item instance for Scene output.
- Ambiguous object annotations fail before SVG serialization.
- The deleted Settings and legacy Theme contracts are not reintroduced.

## Result

M28 is accepted for its defined row-composition and immutable-snapshot scope.
