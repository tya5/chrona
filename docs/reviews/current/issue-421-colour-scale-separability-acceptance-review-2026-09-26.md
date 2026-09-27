<!-- chrona:literal-acceptance/v1 -->

# Release Review — Colour Scale Separability (#421)

**Reviewed product:** `62e389f0` on `main`. **Design:** [design](../../design/issue-421-colour-scale-separability-design-2026-09-26.md), [architecture review](issue-421-colour-scale-separability-architecture-review-2026-09-26.md), Specification 60 §5.1. The work was a single slice (I421-1), so this review also serves as its slice review.

## Evidence and byte review

- **Tests:**
  - [`test_color_separability.py`](../../../tests/unit/chrona/presentation/model/test_color_separability.py) covers:
    - duplicates and near colours named as collisions;
    - a gold/olive pair (24.4 normal, 1.5 under protanopia) reported only when protanopia is claimed;
    - `none-claimed` adds nothing;
    - resolution carries collisions without refusing.
  - [`test_readable_defaults.py`](../../../tests/integration/test_readable_defaults.py) adds:
    - the CLI names `bus`/`launch` with `vision: normal` and `deltaE: 0.0`;
    - no committed Scene carries the warning.
  - Full `pytest`: 1147 passed, 19 skipped. Conformance PASS.
- **Scheme fixes:**
  - `mission-light`: `launch #FBE3E8`, `ops #EAF4D9`; minimum pairwise ΔE00 6.8.
  - `control-room-dark`: `launch #3A1A24`, `ops #2A3314`; minimum 10.7.
  - `print-mono`: a six-step grey ramp `#F3F3F3`…`#848484`; minimum 5.3. It is used by `09-gallery-mono` with the `owner` scale, and was 2.3 before.
- **Public materializers:** all 21 regenerated and `--check` PASS. Changes:
  - `planned` fills and legend swatches on `01`, `02`, `08`, `09` and `11`;
  - provenance only (scheme identity) on the other HALCYON slides;
  - no geometry change;
  - the committed Scenes carry no warning.
- **Contrast:** `presentation-contrast` reports 0 errors. A greyscale PNG of `09-gallery-mono` shows the owner bars in distinct greys with readable labels.

## Literal issue acceptance

### Issue #421

- Source: [Issue #421](https://github.com/tya5/chrona/issues/421)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No colour scale resolves two domain values to the same colour. | met | Committed schemes fixed; [`test_no_committed_scene_ships_an_inseparable_colour_scale`](../../../tests/integration/test_readable_defaults.py). Any duplicate (ΔE00 = 0) is always reported. | — |
| 2 | A scale whose colours are not separable produces a diagnostic naming the colliding values. | met | `W_PRESENTATION_SCALE_NOT_SEPARABLE` with `values`, `vision`, `deltaE`; [`test_cli_names_colliding_scale_values`](../../../tests/integration/test_readable_defaults.py); Scene diagnostic string. | — |
| 3 | The check honours the scheme's declared colour-vision suitability. | met | Claimed deficiencies are simulated (Machado 2009); [`test_claimed_colour_vision_is_checked_and_unclaimed_is_not`](../../../tests/unit/chrona/presentation/model/test_color_separability.py). | — |

## Programme-level criteria (optional)

- CI: [run 36245406749](https://github.com/tya5/chrona/actions/runs/36245406749) on `62e389f0`, green on all four jobs.

## Architecture conclusion

- Pure colour arithmetic lives in `model/color_separability.py`.
- `resolve_color_scale` adds non-fatal collisions; the Scheme's claims reach it through the resolved Theme (`colorVision`).
- The CLI and Scene project the typed collisions. Layout and the adapters are untouched.
- #479's generated palettes will reuse the same check.

Release disposition: all rows met.
