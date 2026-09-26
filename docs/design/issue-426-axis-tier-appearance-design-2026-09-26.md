# Design — Axis Tier Appearance (#426)

**Predecessor:** [Design plan](../planning/active/issue-426-axis-tier-appearance-design-plan-2026-09-26.md). **Depends on:** Specification 39 (axis fitting/thinning), Specification 49 (semantic presentation contract), Specification 60 (declared colour scales, referenced only for the future extension point). **Layer ownership (unchanged):** View states intent (which unit/every/role, and now which named Theme role); Theme states tokens (fonts, fills, opacities) under role keys; Layout owns measurement, lane geometry and placement; Scene carries completed primitives; adapters serialize only.

## 1. Use cases

- **UC1 — two stacked date bands, distinct grounds.** An author declares a `quarter` band tier and a `month` band tier; both render, each confined to its own lane, and a Theme can give them different fills (Editorial: navy quarter ground, light month ground).
- **UC2 — two label tiers, distinct type.** An author declares `quarter` and `month` labels tiers; each can bind a different Theme text role (size, weight, letter-spacing, colour), so the coarser tier can be the visually dominant one.
- **UC3 — an unmodified View is unaffected.** Every committed View today declares one band tier and two labels tiers with no new field; its rendered geometry, semantic ids and Theme role lookups do not change at all.
- **Out of scope (recorded, not built):** UC4 — a band tier resolves a different fill per *interval* from a declared domain (Wallboard's per-quarter hue, and #405's alternating fill). See §6.

## 2. Contract

### 2.1 View (next version after v0.23; number assigned by the lead in phase 2)

One new optional field on an axis tier object, `typographyRole` (string, non-empty, no enum — it names an arbitrary Theme role key, the same open vocabulary `roles` already accepts):

- Allowed on a `labels` tier: selects the Theme text role used to paint that tier's label and to size its lane. Default when omitted: `"axis"` (today's fixed literal).
- Allowed on a `band` tier: selects the Theme role whose `fontSize × lineHeight` sizes that tier's own lane, when it is not the sole band tier (§2.2). It paints nothing; a band's fill is controlled by its semantic id (§2.3), never by `typographyRole`. Default when omitted: `"axis"`.
- Disallowed on `grid-major`/`grid-minor` tiers (unchanged; they span the full timeline block, not an axis lane).

No other View field is added. Fill selection stays entirely a Layout/Theme concern (semantic id per tier, §2.3), matching the issue's own proposal and keeping the schema surface minimal.

### 2.2 Lane geometry (Layout, no schema)

Layout keeps two independent, monotonic lane cursors over `request.surface_content.axis_tiers`, in declared order, each starting at `axis.bounds.block`:

- **Label lane cursor** — unchanged mechanism, now parameterized per tier: a `labels` tier's lane height is `text_treatment(tier.typography_role or "axis").font_size * line_height` (horizontal orientation; unchanged rotated-orientation formula for `rotate-cw`/`rotate-ccw`), and its origin is the cumulative height of prior `labels` tiers.
- **Band lane cursor** — new, symmetric: a `band` tier's lane height is `text_treatment(tier.typography_role or "axis").font_size * line_height`, origin is the cumulative height of prior `band` tiers. `grid-*` tiers advance neither cursor (unchanged; they are not lanes).

**Byte-identity carve-out.** When exactly one `band`-role tier is declared (every corpus View today), Layout keeps today's literal rect — `Rect(x, axis.bounds.block, x2-x, axis.bounds.block_size)`, i.e. the whole axis slot — instead of the one-lane-cursor formula above. This is the only conditional in the design and exists solely so no committed View's Scene output changes. It activates the new per-lane formula only once a second `band` tier appears. This asymmetry is intentional, not an oversight: a View author who adds a second band tier will see the first band's height drop from "whole axis" to "its own lane," which is documented in §5 as an authoring note, not silently patched around.

Two tiers of the *same* role never overlap, by construction of a single monotonic cursor per role. Two tiers of *different* roles (one band, one labels) coincide exactly when both bind the same `typographyRole` and occupy the same ordinal position among tiers of their own role (e.g., the first declared band and the first declared labels tier both left at the default `"axis"` role): both cursors start at the same origin and advance by the same height. This is how the Editorial reference is reproduced: bind the quarter band and the quarter labels tier to one role (e.g. `axisQuarter`), and the month band and month labels tier to another (`axisMonth`); the Theme gives those two roles the desired 52px/48px-equivalent line metrics, and the two pairs' lanes coincide without Layout ever comparing them to each other by unit or adjacency.

Neither cursor is told about the other's tier order; there is no unit-matching or positional pairing rule. This is deliberately the same "give it its own lane, the mechanism labels already have" mechanism the issue proposes for bands, applied twice (once per role), not a new joint concept. An author who wants two lanes to coincide binds the same role to both tiers in the pair; an author who does not, gets two independently-stacked, non-coincident bands and two independently-stacked, non-coincident label rows — still each in its own lane, still not covering another lane of the same role, which is exactly literal criterion 1.

Overflow: if the band cursor's cumulative height exceeds `axis.bounds.block_size`, Layout raises the same class of diagnostic the label lane already raises for `E_PRESENTATION_AXIS_OVERFLOW` (exact diagnostic id decided in phase 2 implementation, not a new contract concept).

### 2.3 Semantic ids (Layout, closed vocabulary, no schema)

`semantic_registry.py`'s vocabulary is a closed, curated list by its own docstring ("every visual meaning ... is declared here once"); this design adds to it rather than making it open-ended:

- Band tiers, in declared order among band-role tiers: 1st → `axisBandDecoration` (unchanged; existing Theme bindings need no edits), 2nd → `axisBandDecoration2`, 3rd → `axisBandDecoration3`. Each is a new fixed `SemanticBinding` entry (`primitive_kind="decoration"`, `theme_role` `"axis-band-decoration2"`/`"3"` respectively, mirroring the first entry's naming), added to `BACKGROUND_SEMANTIC_IDS`.
- Label tiers, in declared order among labels-role tiers: 1st → `axisLabel` (unchanged), 2nd → `axisLabel2`, 3rd → `axisLabel3`. Each is a new fixed `SemanticBinding` entry mirroring `axisLabel`'s shape (`theme_role="axis2"`/`"axis3"` as the registry's own nominal default; the text actually painted still uses the tier's resolved `typographyRole`, passed explicitly to `place_text`, exactly as today for the single label case).

Two ordinals beyond the first are enough for literal criteria 1-4 (two bands, two labels); a future author declaring a third tier of either role registers a third id, exactly as adding any other semantic meaning does today.

### 2.4 Two call sites generalize from one literal id to the closed set

- `layout/surface_composer.py::axis_band_host` currently selects a hosting band by inline (x) containment alone. It must also require block/lane containment (the label's baseline lane falls inside the band's block range), so a label is hosted by the band actually behind it once bands occupy different lanes, not by whichever band's x-range happens to be widest.
- `layout/surface_quality.py`'s `E_LAYOUT_TEXT_HOST_INVALID` check (`item.semantic_id == "axisLabel"` → `host.semantic_id == "axisBandDecoration"`) generalizes to two small closed frozensets — axis-label ids and axis-band ids from §2.3 — preserving the invariant it exists for (an axis label may only be hosted by an axis band, never an arbitrary shape) rather than weakening it to "any shape."

## 3. Migration and compatibility

No existing View, Theme or Color Scheme file changes. The single-band carve-out (§2.2) and the `"axis"` default for `typographyRole` (§2.1) together guarantee every corpus View's Scene output is byte-identical: the new code paths are reachable only by declaring a second tier of a role, or by declaring `typographyRole` explicitly, neither of which any committed View does.

The new example (§4) is either a new slide in an existing example package or a derived Theme (a Theme that inherits from a shipped one and adds the two new roles plus their fills), whichever keeps the diff smallest; the exact choice is a phase-2 implementation decision, not a design one, since the design does not depend on it.

## 4. Committed example

A new slide (or the same slide under a derived Theme) declaring:

```yaml
axis:
  tiers:
  - {unit: quarter, every: 1, role: band,   typographyRole: axisQuarter}
  - {unit: quarter, every: 1, role: grid-major}
  - {unit: quarter, every: 1, role: labels, typographyRole: axisQuarter, label: {form: year-quarter, ...}}
  - {unit: month,   every: 1, role: band,   typographyRole: axisMonth}
  - {unit: month,   every: 1, role: labels, typographyRole: axisMonth, label: {form: short-month, ...}}
```

with a Theme (derived, so shipped Themes are untouched) declaring `roles.axisQuarter`/`roles.axisMonth` typography and `roles.axisBandDecoration`/`roles.axisBandDecoration2` fills bound to two visually distinct Scheme colours, and `colorBindings` giving `axisLabel`/`axisLabel2` (or whichever role the text paints from) two distinct text colours, e.g. white-on-navy for the quarter lane and dark-on-light for the month lane, reproducing the Editorial reference's visual distinctness.

## 5. Authoring note (for the specification amendment)

Adding a second `band`-role tier to a View that had exactly one changes that first band's rendered height, because the whole-axis-fill behavior applies only while a View has exactly one band tier. This is stated as normative behavior in the Specification 39 amendment accompanying this design, not left as an implicit side effect.

## 6. What is deliberately not built: per-interval fills (#405)

The folded-in #405 comment — "a band tier can resolve alternating fills from a Theme, and a committed slide shows it," generalized in the later comment to Wallboard's per-quarter hues via a colour scale keyed by the interval — **is not met by this design and is not a literal criterion of #426.** It is kept architecturally open at no cost to this phase:

- Today (and unchanged by this design), the band tier's fill lookup — `request.theme_tokens.background(semantic_binding(<band id>).scene_role)` — is already evaluated once *per interval*, inside the `for interval in intervals:` loop, not once per tier. A follow-on issue can replace the constant `<band id>`/role passed on each iteration with one selected by `interval.index % N` (alternation) or by a Theme `colorScales` lookup (Specification 60) keyed by the interval's natural bucket, without touching the lane-cursor or semantic-id design in this document.
- Specification 60's colour scales are currently eligible only for `planned` member marks with a Project-field-tagged domain (§1 of that specification). Extending eligibility to axis bands keyed by interval ordinal (not a Project field) is a genuine new View/Theme surface — a new eligible-target case, not a natural fit for the existing `field`-tagged encoding — and is named here as a successor issue, not built.

## 7. Risks

- The single-band carve-out (§2.2) is a real special case; if the lead prefers a uniform rule with no carve-outs, every corpus View's axis geometry changes and public evidence must be regenerated and attributed for all 21 materializers rather than the one new example. This trade-off is called out for the architecture review, not decided unilaterally here.
- Pre-registering only two ordinals beyond the first (§2.3) is a deliberate, minimal, closed vocabulary; a third or later ordinal is a small, mechanical follow-up, not a redesign.
