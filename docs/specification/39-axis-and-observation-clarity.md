# Axis and Observation Clarity

**Status:** Design complete — Issue 36
**Depends on:** Specifications 36 and 38.

## 1. Axis fitting

Axis level selection evaluates each candidate interval by its natural calendar bucket width, before the View window clips its first or last bucket. Rendering geometry remains clipped to the View window. A clipped edge label that cannot fit is omitted; it does not reject an otherwise fitting level. Interior labels continue to require measured fit. The Axis formatter is the sole source of label text.

### 1.1 `thin-with-record` disposition (#482)

The same principle governs one label tier's own thinning: a candidate whose own clipped interval cannot hold its measured label is omitted, on that reason alone, and never causes another candidate to be omitted. `thin-with-record` disposition depends only on each candidate's own measured fit; it does not select a periodic stride or phase across the tier, because axis buckets are contiguous and half-open, so a candidate that fits inside its own bucket cannot reach a neighbour's bucket regardless of any other candidate's disposition. One collision removes exactly one label.

## 2. Missing Actual

A missing-actual primitive exists only when `comparison.facets` includes
`missingActual` and the View-projected observation state is `due-unobserved`:
no selected Actual observation exists and the planned exclusive span end or
point `at` is on or before the Actual set's explicit `asOf`. Work after that
date has no missing-Actual mark. An incomplete but present observation is
`recorded`, not missing. Layout anchors completed geometry to the planned end
or point and Scene projects it; neither recomputes the due predicate. The
primitive remains optional and has no scheduling effect.

## 3. Dependencies

Dependency paths remain Scene-owned. Their stroke token is Theme-owned by the `dependency` role. Shipped schemes bind that role to `textMuted`, not `neutral`, to meet the examples' visible secondary-ink role. No renderer color fallback or per-example branch is allowed.

## 4. Acceptance

- a clipped tail cannot downgrade an otherwise fitting axis level;
- edge labels are omitted only when their clipped geometry cannot fit;
- `thin-with-record` omits only a label whose own clipped interval cannot hold it, never a label that fits because another candidate does not;
- missing-actual is absent when the facet is not selected or the item is not yet due, and otherwise follows its planned mark;
- dependency primitives consume the declared dependency role; and
- no Project, Snapshot, Actual, legacy Settings, or legacy Theme contract changes.
