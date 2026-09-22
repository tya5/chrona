# Gantt Comparison Groups and Legend — I58-4 Implementation Plan

**Status:** Design and implementation plan. Begins only after I58-3 merge `38517ff`.

## Purpose and boundary

I58-4 makes group headers and legends explicit public resource choices. It does
not add scheduling semantics, renderer-specific behavior, new label/routing
policy, or a Scene geometry path. The completed placement types from I58-1 are
used, but do not by themselves satisfy this slice.

## Closed design

View `grouping.presentation` is `band` or `header`. `header` requires a
positive resolved `timeline.groupHeader.blockSize`; Layout reserves exactly one
header band before each contiguous non-empty group and either emits its measured
header placement or raises `E_LAYOUT_GROUP_HEADER_OVERFLOW`.

A Layout Profile `legend` slot is the only geometry authority for legends.
Selected Detail Profile entries are ordered semantic roles; each entry produces
exactly one role-derived swatch and one measured label when the slot exists.
Without the slot, no legend primitive is emitted. Slot overflow controls the
same declared fit/diagnose behavior as other Layout slots.

## Atomic implementation

1. Add View schema/ingress normalization and neutral group-capacity fixtures.
2. Make Layout use only normalized group presentation and enforce its capacity;
   preserve Scene as a projection of Layout placements.
3. Add neutral legend-slot ordering/absence/overflow fixtures and structural
   projection tests.
4. Adapt only HALCYON contexts for which headers or a legend aid the declared
   reader task, then regenerate SVG/PNG evidence in this single PR.

## Acceptance and release unit

A58-05 requires visible measured headers for enabled groups, an absent-slot
legend with no primitives, complete swatch/label pairs for a present slot, and
stable diagnostics for missing header capacity. Focused tests, full pytest,
public materializer byte checks, and declared-viewport PNG review precede the
implementation PR. The design and final implementation reviews each check the
Project → View/Detail/Layout Profile → Layout → Scene → SVG/PNG boundary.
