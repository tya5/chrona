# Axis and Observation Clarity

**Status:** Design complete — Issue 36
**Depends on:** Specifications 36 and 38.

## 1. Axis fitting

Axis level selection evaluates each candidate interval by its natural calendar bucket width, before the View window clips its first or last bucket. Rendering geometry remains clipped to the View window. A clipped edge label that cannot fit is omitted; it does not reject an otherwise fitting level. Interior labels continue to require measured fit. The Axis formatter is the sole source of label text.

### 1.1 `thin-with-record` disposition (#482)

The same principle governs one label tier's own thinning: a candidate whose own clipped interval cannot hold its measured label is omitted, on that reason alone, and never causes another candidate to be omitted. `thin-with-record` disposition depends only on each candidate's own measured fit; it does not select a periodic stride or phase across the tier, because axis buckets are contiguous and half-open, so a candidate that fits inside its own bucket cannot reach a neighbour's bucket regardless of any other candidate's disposition. One collision removes exactly one label.

## 1.2 Axis tier appearance (#426)

An axis tier's `role` decides what it draws; a new optional `typographyRole`
(introduced after View v0.23) decides what Theme role measures its text and
sizes its lane. A `labels` tier's colour is resolved separately through its
ordinal Scene visual role (`axisLabel`, `axisLabel2` or `axisLabel3`), not through
the arbitrary `typographyRole`; see the [#478 admission amendment](../design/issue-478-axis-typography-role-admission-amendment-2026-09-27.md).
Layout keeps one independent, monotonic lane cursor
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

The date form is `localized-date`, `day-month` (`20 Aug`; `8月20日` in `ja-JP`) or
`day-month-year` (`20 Aug 2027`; `2027年8月20日`), each a template of the built-in axis name
tables (#991; the heading's `dateForm`, Spec 06 section 7.4, takes the same three). The marker also
declares an optional `placement`: `top` (the default) searches the plot's top margin beside the rule,
then the rule-hosted positions; `foot` searches the plot foot, first centred on the rule, then beside
it, then the rule-hosted positions. A marker without `placement` and `day-month` forms behaves as before.

Any label whose semantic has a registered chip binding (`asOfLabelChip`,
`memberLabelChip`, `finishDeltaChip`, `periodLabelChip`) may carry a chip. A chip is drawn when
the Theme declares the binding's role (`as-of-label-chip`,
`member-label-chip`, `finish-delta-chip`, `period-label-chip`) with `backgroundTreatment: fill`,
optional `chipPadding` (a ratio of the label's font size inline, and half of
it on the block axis) and optional `markCornerRadius` (a ratio of the chip's
block size). Layout inflates the label's footprint by the padding before
candidate search, and completes the chip Rect under the text. Contrast is
checked against the chip as the text's ground.

## Axis lanes, cells and rule (#426)

- A labels tier whose typography role declares `laneBlockSize` is a declared lane. Lanes stack from the top of the axis slot in labels-tier order, and each label's line box is centred in its lane. A band tier with the same `unit` fills exactly that lane.
- A band role's `cellGap` insets each cell by half the gap at both inline ends, except the outer end of a cell at the window edge, which reaches the plot edge (Spec 50, the plot, #880). A bound `axis-cell-separator` role draws a separator at each interval start inside the axis, spanning the declared lanes or the whole slot.
- A bound `axis-rule` role draws the axis/plot boundary along the bottom of the axis slot; every shipped Theme binds it.
- An axis label role's `labelInset`, a ratio of its font size, insets start-aligned labels from their cell edge.
- A Theme that declares none of these renders the axis as before.

## Axis ticks (#492)

- An optional `tickLength` (a named number token, px) on the `axis-major` or `axis-minor` role turns the marks of every `grid-major` or `grid-minor` tier bound to that role into ticks. Each tick is a two-point Path that stands on the axis rule: it runs from the bottom edge of the axis slot up by `tickLength`.
- The marks are the same interval starts as the full-height line, for any unit (a week tier gives week ticks); identity, semantic ids and paint are unchanged, so existing colour, stroke width and dash bindings apply.
- Without `tickLength` the mark spans the plot as before. A non-positive `tickLength` is `E_PRESENTATION_AXIS_INVALID`; a length greater than the axis slot block size is `E_PRESENTATION_AXIS_OVERFLOW`. Neither is clamped.
- Design: [#492](../design/issue-492-axis-ticks-design-2026-10-02.md). The property is added in place to Theme v0.11 and v0.13 (Specification 56 section 3.2).

## Axis secondary labels (#493)

- A `labels` tier of a fixed `unit` and `orientation: horizontal` may declare `label.secondary: {form, nameTable?, typographyRole, placement}`: a second form of the same interval, formatted by the selected name table (the primary's table when `nameTable` is omitted), drawn in the same cell. `form`, `typographyRole` and `placement` (`stacked` or `inline`) are required. A tier with `unit: auto` or a rotated orientation cannot declare one.
- The secondary is measured with the same text measurement as the primary (`measure_text_width` with the font metrics of its own `typographyRole`); no width is a constant. It takes its size, weight, family and transform from its own Theme text role (`axisSecondary` is admitted beside `axisMonth`) and its colour from the tier's ordinal label role, so every Theme that colours the tier colours the secondary.
- The secondary's typography role may declare `labelGap`, a ratio of that role's own font size (a named number token, like `labelInset`). Absent, the gap is 0 for `stacked` and one measured space of the primary's role for `inline`. `stacked` draws the secondary on the line below the primary, a gap below it, aligned like the primary (`start` at the label inset, `center` centred, each line on its own); `inline` draws it after the primary on the primary's baseline, a gap after it, the pair aligned as one unit. The cell then occupies `Hp + gap + Hs` (stacked) or the shared-baseline extent of the two texts (inline), `Hp` and `Hs` being the line boxes of the two roles. If that does not lie inside the tier's declared lane, or inside the axis slot for an undeclared lane, Layout raises `E_PRESENTATION_AXIS_OVERFLOW` (detail `secondary-lane:<tier>`).
- A secondary is drawn only in a cell whose primary is placed and fits. It never changes the primary's fit, thinning or automatic-unit selection. When it does not fit its cell (stacked: wider than the cell's available inline size; inline: primary, gap and secondary wider than it) it is omitted, the primary is drawn as without a secondary, and Layout records `W_LAYOUT_AXIS_SECONDARY_OMITTED:<primary id>:<reason>` (`does-not-fit`, or `primary-does-not-fit` for a primary placed under `visible-overflow`) with a suppressed placement decision. There is no ellipsis. A thinned primary draws neither text.
- The block position of a stacked tier is fixed per tier, so a cell whose secondary is omitted keeps its primary on the upper line. A drawn secondary is `axis-label-secondary:<tier>:<index>`, hosted like the primary, so the Scene perceptibility checks (text intersection, occlusion, paint contrast) apply to it unchanged.
- A View without `secondary` renders as before. The View property is added in place to View v0.28, and `labelGap` to Theme v0.11 and v0.13 (Specification 56 section 3.2). Design: [#493 work record](../archive/planning/issue-493-axis-secondary-label-2026-10-02.md).

## Axis cell corners (#491)

- A band role (`axis-band-decoration`, `axis-band-decoration2`) may declare one corner shape for the cells of the band tier bound to it: `cellCornerRadius` (rounded corners) or `cellCornerChamfer` (cut corners), each a named number token beside `cellGap`. The value is a ratio of the cell's block size (its lane height, or the axis slot for a single band tier), `0 < ratio <= 0.5`, and applies to all four corners of every cell.
- Declaring both, a ratio not above 0 or above 0.5, or `cellCornerChamfer` together with a Theme `pattern` on the same role, is `E_PRESENTATION_AXIS_INVALID` (detail `cell-corner-both:<tier>`, `cell-corner:<tier>`, `cell-chamfer-pattern:<tier>`). Nothing is clamped.
- The applied size of a cell is `min(ratio * block size, cell inline size / 2)`, the cell being the rect drawn after the `cellGap` inset and the plot-edge extension. A cell narrower than twice the requested size is drawn with the reduced size and Layout records `W_LAYOUT_AXIS_CELL_CORNER_REDUCED:<placement id>`; a cell of zero width has no corner.
- Every cell has the same rule applied to its own rect and does not depend on its neighbours: cells with a `cellGap` are separate tiles, abutting cells show a notch at each shared edge, and the first and last cell (including a cell that reaches the plot edge) round or cut their outer corners like any other. The outline lies inside the cell rect and so inside the axis slot. Identity (`axis-band-rect:<tier>:<index>`), paint order, visual role and label hosting are unchanged.
- Radius is a Scene `Rect` with `corner_radius`; chamfer is a closed polygon carried as a Scene `Symbol` outline. The Scene occlusion check treats an opaque band `Symbol` cell as it treats a band `Rect`. SVG, PNG (resvg) and TikZ draw both; the Typst adapter draws a radius and rejects a chamfer with `E_VISUAL_CAPABILITY_UNSUPPORTED`.
- A Theme that declares neither renders as before. The properties are added in place to Theme v0.11 and v0.13 (Specification 56 section 3.2). Design: [#491 work record](../planning/active/issue-491-axis-cell-corners-2026-10-02.md).
