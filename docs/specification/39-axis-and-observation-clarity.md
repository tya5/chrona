# Axis and Observation Clarity

**Status:** Design complete — Issue 36
**Depends on:** Specifications 36 and 38.

## 1. Axis fitting

Axis level selection evaluates each candidate interval by its natural calendar bucket width, before the View window clips its first or last bucket. Rendering geometry remains clipped to the View window. A clipped edge label that cannot fit is omitted; it does not reject an otherwise fitting level. Interior labels continue to require measured fit. The Axis formatter is the sole source of label text.

### 1.1 `thin-with-record` disposition (#482)

The same principle governs one label tier's own thinning: a candidate whose own clipped interval cannot hold its measured label is omitted, on that reason alone, and never causes another candidate to be omitted. `thin-with-record` disposition depends only on each candidate's own measured fit; it does not select a periodic stride or phase across the tier, because axis buckets are contiguous and half-open, so a candidate that fits inside its own bucket cannot reach a neighbour's bucket regardless of any other candidate's disposition. One collision removes exactly one label.

## 1.2 Axis tier appearance (#426)

An axis tier's `role` decides what it draws; a new optional `typographyRole`
(next View version after v0.23) decides what Theme role sizes and, for a
`labels` tier, paints it. Layout keeps one independent, monotonic lane cursor
per role among `band` and `labels` tiers (`grid-major`/`grid-minor` remain
full-height and outside any cursor, unchanged): the Nth `band`-role tier
occupies the Nth band lane, the Nth `labels`-role tier occupies the Nth label
lane, and a lane's height is `text_treatment(typographyRole or "axis")`'s
`fontSize × lineHeight`. Two tiers of the same role never overlap. Two tiers of
different roles (one band, one labels) coincide exactly when both are given
the same `typographyRole` and hold the same ordinal position among tiers of
their own role; Layout does not pair a band and a labels tier by unit or
adjacency.

A View with exactly one `band`-role tier keeps its band's historical geometry:
the rect spans the whole axis slot (`axis.bounds.block`/`block_size`), not a
one-line lane. Adding a second `band`-role tier changes the first band's
rendered height, from the whole axis slot to its own lane; this is normative,
not a defect. `typographyRole` defaults to `"axis"` when omitted, so a View
that never declares it is unaffected by this section.

Each band-role tier resolves a Theme role through its own semantic id —
`axisBandDecoration` for the first declared band tier, `axisBandDecoration2`
for the second, `axisBandDecoration3` for the third — so two band tiers may
take different fills. Each labels-role tier similarly resolves through
`axisLabel`, `axisLabel2`, `axisLabel3`, so two labels tiers may take different
sizes, weights and colours. A label's host band (for paint order and text
contrast) is the band tier whose lane contains that label's own lane, not
merely the band whose inline span contains the label's x-position.

Resolving a band tier's fill per *interval* (an alternating fill, or one fill
per coarser-interval domain as in a wallboard treatment) is out of scope for
this section. The per-interval Theme lookup this would need is already
evaluated once per interval inside Layout's existing band loop; only the role
selected on each iteration would need to become data-driven. It is recorded as
a successor to Specification 60 (declared colour scales), not built here.

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
- no Project, Snapshot, Actual, legacy Settings, or legacy Theme contract changes;
- a View declaring two `band` tiers renders both, each confined to its own lane, neither covering the other;
- two `band` tiers may resolve different fills from a Theme;
- two `labels` tiers may resolve different sizes, weights and colours from a Theme;
- a View declaring exactly one `band` tier is unaffected: its band still spans the whole axis slot.

## As-of label content and label chips (#428)

From View v0.23, an `asOf` marker's `label` is rendered exactly as written. A
date is added only when the marker declares `date: {form: localized-date}`
(optionally with `nameTable`). It is then formatted by the axis name table
exactly like an axis `localized-date` label and follows the label, separated by
a space. A View without an `asOf` marker keeps the implicit label
`As of <localized date>`.

Any label whose semantic has a registered chip binding (`asOfLabelChip`,
`memberLabelChip`, `finishDeltaChip`) may carry a chip. A chip is drawn when
the Theme declares the binding's role (`as-of-label-chip`,
`member-label-chip`, `finish-delta-chip`) with `backgroundTreatment: fill`,
optional `chipPadding` (a ratio of the label's font size inline, and half of
it on the block axis) and optional `markCornerRadius` (a ratio of the chip's
block size). Layout inflates the label's footprint by the padding before
candidate search, and completes the chip Rect under the text. Contrast is
checked against the chip as the text's ground.
