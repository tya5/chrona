# Design — Axis Ticks at Interval Starts (#492)

**Plan:** [design plan](../planning/active/issue-492-axis-ticks-design-plan-2026-10-02.md). **Normative home:** [Specification 39](../specification/39-axis-and-observation-clarity.md), "Axis ticks (#492)". **Builds on:** the [#426 cells correction](issue-426-axis-cells-correction-2026-09-27.md).

A Theme that does not declare the new property renders exactly as today, byte for byte. No View version is needed.

## Decision 1 — where the intent lives (owner decision)

| Option | What it is | Result |
| --- | --- | --- |
| A | A new View tier role `tick`. | Rejected: widens the View enum, and a View then names an appearance (a short mark) that a Theme swap could not change. |
| **B** | An optional Theme role property `tickLength` on the existing `axis-major` and `axis-minor` roles. | **Chosen.** |

Why B: a `grid-major` / `grid-minor` tier already means "a mark at every interval start of this unit". The View chooses the unit and the role (where marks fall); the Theme chooses how far a mark extends. The same View then renders as full-height lines under one Theme and as short ticks under another, which is how presets differ. **Reversal:** add a View tier role later that reads the same `tickLength`; B stays valid.

## Decision 2 — behaviour

- A `grid-major` or `grid-minor` tier whose bound Theme role (`axis-major` or `axis-minor`) declares `tickLength` (a named number token, px) draws each interval-start mark as a **tick**: a two-point Path that **stands on the axis rule**. It runs from the bottom edge of the axis slot up by `tickLength`.
- The set of marks is unchanged: one per interval start, including a clipped first interval at the window start, exactly the positions the full-height line has today. Only the extent differs.
- Any unit is allowed, so a week tier gives week ticks.
- Identity is unchanged: placement ids `axis-grid:{tier}:{index}`, semantic ids `axisGrid` / `axisGridMinor`, Scene roles `axis-major` / `axis-minor`, paint order unchanged. The colour, stroke width and dash of the tick are those of the same role, so existing bindings carry over.
- Without `tickLength` the mark spans the plot, as today.
- **Failure behaviour.** `tickLength <= 0` raises `E_PRESENTATION_AXIS_INVALID` (detail `tick-length:<role>`); `tickLength` greater than the axis slot block size raises `E_PRESENTATION_AXIS_OVERFLOW` (detail `tick-length:<role>`), the same family the band lanes use. Neither is silently clamped.

## Decision 3 — schema

`tickLength` is added in place as an optional role property (named token, like `laneBlockSize`) to Theme v0.11 and v0.13, with no version bump, per Specification 56 section 3.2. Derived Themes (v0.12, v0.14) validate against the effective schema and need no edit. The change runs `python -m tools.schema_equivalence --base-rev origin/main`; its result is recorded in the implementation PR.

Role admission (`scene/capabilities.py`) admits `tickLength` on `axis-major` and `axis-minor` only, owned by "Layout/Scene completed geometry".

## Decision 4 — the committed slide

A new Controller Z slide `axis-ticks` (view, derived or complete Theme, context, manifest entry, generated SVG and Scene): a quarter band with labels, month labels and full-height month separators, and a **week** `grid-minor` tier drawn as ticks on the axis rule. No existing slide or data is edited.

## Decision 5 — #493

Left open. Two labels in one cell needs a View label-declaration change, a second measured and fitted text, and fit rules; it shares no code with this Theme-declared geometry. See the issue comment.

## Not delivered (recorded, not filed)

- A tick origin other than the axis rule (for example hanging from the top edge of a lane), and a per-tier length: one length per role per Theme. Both are additive successors (a `tickAnchor` role property, a View tier role), only if a target needs them.
