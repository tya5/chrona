# Axis and Observation Clarity

**Status:** Design complete — Issue 36
**Depends on:** Specifications 36 and 38.

## 1. Axis fitting

Axis level selection evaluates each candidate interval by its natural calendar bucket width, before the View window clips its first or last bucket. Rendering geometry remains clipped to the View window. A clipped edge label that cannot fit is omitted; it does not reject an otherwise fitting level. Interior labels continue to require measured fit. The Axis formatter is the sole source of label text.

## 2. Missing Actual

A missing-actual primitive exists only when `comparison.facets` includes `missingActual` and the item has no selected Actual observation. Its geometry is anchored to the item's planned mark: a span attaches at the planned end; a point attaches at the planned point. Scene owns this geometry. The primitive remains optional and has no scheduling effect.

## 3. Dependencies

Dependency paths remain Scene-owned. Their stroke token is Theme-owned by the `dependency` role. Shipped schemes bind that role to `textMuted`, not `neutral`, to meet the examples' visible secondary-ink role. No renderer color fallback or per-example branch is allowed.

## 4. Acceptance

- a clipped tail cannot downgrade an otherwise fitting axis level;
- edge labels are omitted only when their clipped geometry cannot fit;
- missing-actual is absent when the facet is not selected and otherwise follows its planned mark;
- dependency primitives consume the declared dependency role; and
- no Project, Snapshot, Actual, legacy Settings, or legacy Theme contract changes.
