# Design — Colour Scale Separability (#421)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-421-colour-scale-separability-design-plan-2026-09-26.md). **Authorities:** Specifications 34 and 60.

## Contract

**Owner: the presentation model.** A new pure module, `presentation/model/color_separability.py`, provides:
- `delta_e_2000(first_hex, second_hex)`, the CIEDE2000 colour difference of two sRGB colours;
- `simulate(hex, vision)` for `protanopia`, `deuteranopia` and `tritanopia`. It uses the Machado, Oliveira and Fernandes (2009) matrices at severity 1.0, applied in linear RGB.
- `MINIMUM_CATEGORY_DELTA_E = 5.0`. ΔE00 ≈ 2.3 is a just-noticeable difference for adjacent patches. At 5, two categories are distinguishable at a glance on small marks, and the current corpus's distinct pairs pass (minimum 7.6). The value is a named constant, documented in Specification 60.

**Resolution.**
- `resolve_color_scale(..., color_vision=())` compares every pair of resolved domain colours:
  - under normal vision;
  - under each vision the scheme claims in `suitability.colorVision` (`none-claimed` adds none).
- A pair whose ΔE00 falls below the minimum, including an exact duplicate (ΔE00 = 0), becomes a `ScaleCollision(scale_id, first, second, vision, delta_e)` on the `ResolvedColorScale`. Collisions are ordered by domain order, then vision.

**Transport.**
- The render use case passes the Scheme's declared claims. It then projects each collision:
  - as a `W_PRESENTATION_SCALE_NOT_SEPARABLE` CLI warning with `scaleId`, `values`, `vision` and `deltaE`;
  - as a Scene diagnostic `W_PRESENTATION_SCALE_NOT_SEPARABLE:<scale>:<first>:<second>:<vision>`.
- Rendering continues: nothing is refused, and nothing is silent.

**Corpus.**
- `control-room-dark` and `mission-light` give `launch` and `ops` their own category colours, each at least ΔE00 5 from every other `owner` value.
- A test asserts that no committed Scene carries the warning.
- A unit test asserts that any declared scale resolved with a committed View and Scheme meets the minimum.

## Boundaries

No Theme or View syntax change. Scene paint is unchanged except the fixed Scheme colours, which also paint group bands bound to those categories. The adapters are untouched.

#479's "colour by field without listing values" (a palette by first appearance) will reuse this check on its generated palette.

## Tests

- An exact duplicate is reported with both values named.
- A near pair below 5 is reported.
- A pair that passes normal vision but collapses under a claimed deuteranopia is reported only when claimed.
- `none-claimed` adds no vision.
- CLI warning JSON.
- The Scene diagnostic.
- No committed Scene carries the warning.
