# Prototype Evidence — Group Bands and Headers (#481)

This is evidence for the [#481 design plan](../../planning/active/issue-481-group-bands-and-headers-design-plan-2026-09-26.md), not a selected contract. Collected from an unpublished, throwaway prototype on `bf98f9b0`. Baseline: focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`) — 719 passed, 1 skipped.

## Reproduction fixture

`.venv/bin/chrona preset copy control-room-dark --output work/crd`, then `work/crd/layout.yaml` `reviewSurface.backgroundExtents` and `work/crd/view.yaml` `body.backgroundDecoration` edited per case below, rendered against `examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml`.

## Candidate 1: stripe/band emission order (defect 1)

Prototype: in `compose_surface_layout`, emit the group-band/header-band loop before the row-stripe loop (both loops unchanged otherwise), so a same-`paintOrder` row stripe is the later (topmost) primitive.

| Config | Before (published `main`) | After (prototype) |
| --- | --- | --- |
| `rowBand: both, groupBand: both, groups: all, rows: alternate` | `group:ait` (`paintOrder 10`, opaque fill) painted after and fully covering `row-band:integration` at the same order — the stripe primitive exists in Scene but is invisible in the SVG. | Alternating rows painted with the row-stripe color on top of the group's tint; unstriped rows show the group tint underneath. Confirmed visually: PNG crop of the HALCYON‑1 render (rows 130–340 px) with `group-band.fill` set to a distinct color (`neutral`) from `row-band.fill` (`surfaceRaised`) shows a clear two-tone banding — striped rows lighter, unstriped rows the group's darker tint — across the whole table+timeline extent. |

No focused-test run against this candidate in isolation (combined with candidates 2–3 below).

## Candidate 2: group band as outline (defect 1, alternate technique)

Prototype: `work/crd/theme.yaml` `group-band.backgroundTreatment: outline` plus the required `strokeWidth: stroke-width` and a new `group-band.stroke: neutral` binding (both absent from the shipped preset). No `surface_composer.py` change.

Result: renders without error (`E_THEME_ROLE_REQUIRED` is *not* raised — outline-treatment shapes are excluded from the translucent-overlap check, which only inspects `treatment == "fill"`). PNG crop confirms row stripes remain fully visible with a thin group outline traced around the group's extent. This technique already works on `main`; it needs no code change, only Theme authoring (which none of the five shipped presets currently do for `group-band`).

## Candidate 3: header-inclusive group band + gated header-band (defect 2)

Prototype: group-building loop folds the header block into `content_bounds` when a header exists; the header-band shape is gated by the same `banded` selection used for the body band under `groups: all|alternate`, remaining unconditional under `groups: none`.

Config `presentation: header, groups: alternate`: before, `group-header-band:bus` (`bus` not selected, index 1) painted unconditionally at `block: 307.1`, flush against `group:ait`'s tail (`block 157.1 + blockSize 150.0 = 307.1`), both bound to the same fill (`surfaceRaised`) — `bus`'s header reads as `ait`'s last row. After: `bus` gets neither a header band nor a body band (fully unbanded); `ait`'s own band (selected) now spans `block 137.1` (its own header start) through `307.1`, i.e. includes its own header. The "orphan header" adjacency disappears because the unselected group carries no decoration at all.

## Candidate 4: `groupHeader` typography role (defect 3)

Prototype: `typography_role="text"` → `"groupHeader"` (plus `semantic_id="groupHeader"`) at the group-header `place_text` call.

- `control-room-dark` (declares `groupHeader.fontWeight: weight.bold`): emitted `textLayout.weight` changes `400 → 700` for all six `group-header:*` primitives in the HALCYON‑1 render — confirms the Theme role now reaches Scene.
- `mission-light`, `print-mono` (also declare `groupHeader`): render unchanged (no error).
- `elevated-light`, `executive-light` (built-in presets; do **not** declare a `groupHeader` typography role): `E_THEME_ROLE_REQUIRED: /body/roles/groupHeader/fontFamily`.
- Full focused suite (`tests/unit/chrona/presentation tests/integration tests/cli`) against the combined prototype: **76 failed, 643 passed** (vs. 719/1 baseline). Every failure traces to one Theme file lacking a `groupHeader` role, loaded by path from a test fixture — no inline test-authored theme dict is affected. The nine files:
  - `src/chrona/resources/presets/bundles/elevated-light/theme.yaml`
  - `src/chrona/resources/presets/bundles/executive-light/theme.yaml`
  - `examples/aster-ssd/themes/executive-light.yaml`
  - `examples/aster-ssd/themes/onboarding-variation.yaml`
  - `examples/controller-z-ja/themes/executive-light.yaml`
  - `examples/orion-asic/themes/orion-light.yaml`
  - `examples/controller-z/themes/executive-light.yaml`
  - `examples/controller-z/themes/elevated-light.yaml`
  - `examples/controller-z/themes/material-icons-light.yaml`

## Combined prototype

All four candidates together, rendered against every one of the five shipped presets with their default `view.yaml`/`layout.yaml` (`groups: all`, `presentation: header`, and each preset's own `backgroundExtents`): `control-room-dark`, `mission-light`, `print-mono` render unchanged in structure (only the header-inclusive band geometry and bold weight visibly differ, as expected); `elevated-light`, `executive-light` fail with `E_THEME_ROLE_REQUIRED` until the missing `groupHeader` role (and a `groupHeader.fill` paint binding, needed the same way `group-band.fill`/`row-band.fill` are already bound in every shipped Theme) is added.
