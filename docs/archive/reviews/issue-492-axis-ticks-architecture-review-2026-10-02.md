# Architecture Review — Axis Ticks at Interval Starts (#492)

**Decision:** approved for implementation. **Reviewed:** the [design](../../design/issue-492-axis-ticks-design-2026-10-02.md) and the [design plan](../planning/issue-492-axis-ticks-design-plan-2026-10-02.md) against the whole presentation architecture.

| Boundary | Result |
| --- | --- |
| View | No change. The tier, its `unit` and its `grid-*` role already state where marks fall; the schema is untouched (no widening, no version). |
| Theme (v0.11, v0.13) | One optional role property `tickLength`, added in place (Specification 56 section 3.2, the shape of `laneBlockSize`). Omitting it keeps today's behaviour. Derived Themes (v0.12, v0.14) validate against the effective schema. The S0 gate must report it additive. |
| Role admission | `tickLength` is admitted on `axis-major` and `axis-minor` only, owned by Layout/Scene completed geometry; every other role still rejects it. |
| Layout | Owns the geometry. The `grid-*` branch of `compose_axis` reads the property once per role and completes a shorter two-point Path; with no property the existing branch runs unchanged, so bytes are preserved. Invalid or oversized values fail with the existing `E_PRESENTATION_AXIS_*` family, not a silent clamp. No new Layout contract, no change to lanes, labels, bands, separators or the rule. |
| Scene / adapters | Unchanged. The Path primitive, ids, roles and paint order are the same; only its points differ. |
| Collision with adjacent designs | The #426 separators and rule use the same Path family at paint order `BACKGROUND_PAINT_ORDER + 2`; a tick is `+1` as the full-height grid is today, so stacking order is unchanged. #482 thinning and #405/#406 tier selection act on labels and intervals, not on grid extent. The #582, #497 and #718 areas (Project schema and Scene, the legend, packaged presets) are not touched: no preset is edited. |
| Evidence | The default path is byte-identical (the whole corpus is rendered before and after). The committed slide is new; no existing slide changes. |

**Findings:**

1. A Theme property that changes how a View-declared tier looks does not break "View selects, Theme paints": the View names the unit and role, the Theme names the extent, as the #426 `cellGap` and `laneBlockSize` already do.
2. The shared role means a Theme gets one tick length for all `grid-minor` tiers. Accepted; a View-level role or `tickAnchor` is an additive successor if a target needs it.
3. The tick stands on the axis rule whether or not the Theme binds `axis-rule`. Accepted and documented.

**Risk:** a ticks Theme that sets `tickLength` while the axis slot metric is small gets `E_PRESENTATION_AXIS_OVERFLOW`; this is the intended, diagnosable failure.
