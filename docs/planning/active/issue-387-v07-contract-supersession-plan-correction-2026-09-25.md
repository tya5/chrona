# Plan Correction: Declared Vocabulary Integrity v0.7 Supersession (#387)

**Status:** Accepted correction to the #387 implementation plan.

**Corrects:** [Declared Vocabulary Integrity implementation plan](issue-387-declared-vocabulary-integrity-implementation-plan-2026-09-25.md)

**Related completed work:** #384 completed mark geometry, accepted at
`b069f430`.

## Observed public-state change

I387-2 correctly migrated the former scalar Theme marker and pattern contract
to Theme v0.6, where Theme normalization owned the finite accepted names.
Before #387 could be accepted, #384 replaced that intermediate contract with
Theme v0.7 structured, completed marker/pattern/symbol geometry.  Its
inventory policy and generated report were updated in the same published
slice.  `main` therefore has no live Theme v0.6 resource or reader.

This is not a regression and must not be repaired by restoring v0.6.  The
#387 design explicitly permits #384 to replace the scalar names when it moves
the complete Theme-to-Scene contract and its owner evidence together.

## Corrected acceptance basis

I387-3 shall assess the current Theme v0.7 boundary, not the superseded v0.6
intermediate boundary:

1. `tools/vocabulary_inventory.py --check` must compare each registered
   finite Theme v0.7 field with its Theme-owned accepted set and reject a
   declaration wider than that set.
2. Theme normalization and Scene construction must own resolved marker,
   pattern, and symbol geometry; adapters must not select Theme vocabulary.
3. The closed Render Context locale pair and the required View annotation
   anchor continue to be checked at their respective resource boundaries.
4. No live closure may reference Theme v0.6, View v0.12, or Render Context
   v0.14.

## Architecture consistency review

The correction preserves the accepted authority flow:

```text
schema/resource -> Theme, Context, or View normalization -> Layout -> Scene -> adapter
repository inventory -> generated quality evidence only
```

The v0.7 migration strengthens, rather than weakens, the #387 boundary:
adapters receive completed primitive geometry instead of scalar Theme names.
It does not centralize vocabulary policy in the inventory, alter scheduling or
Project semantics, or introduce a compatibility reader.  #384's acceptance
review supplies the Theme/Scene materializer and generated-artifact evidence;
#387 retains responsibility for the declared-vocabulary gate and the Context
and View boundaries.

## Publication gate

Publish this correction before the #387 acceptance review.  Then re-run the
current focused inventory/owner tests, conformance, full pytest, public
materializer byte checks, generated SVG diff review, and three-platform CI.
The acceptance review must cite Theme v0.7 explicitly and explain the
supersession so future work does not infer that v0.6 remains supported.
