# Issue #429: group tint for every valued grouping, then register target-b (work record)

Living record for slice P429-5 of [#429](https://github.com/tya5/chrona/issues/429). Edited in place. Decision source: the reviewer's answer on #429 (gap 2, 2026-10-14).

**Public base:** `24374ec85` on `main`.

## Baseline

- `target-b` declares a default `grouping.tint: {scale: owner}`. `owner` names the Theme's `colorScales.owner`, not a project field.
- Specification 50 ("Group tint") and `_group_tint` restrict `grouping.tint` to `grouping.by: field`. The generic design View groups by `objectType`, so the tint raised `E_VIEW_GROUP_TINT_UNUSABLE` and `target-b` could not be registered.

## Rule

`grouping.tint` applies to every grouping whose groups have values; the domain stays `firstAppearance` in display order unless listed.

| `grouping.by` | Group values | Tint |
| --- | --- | --- |
| `field` | the field values | unchanged (HALCYON target-b groups by `field: owner`; output byte-identical) |
| `objectType` | the object type names | now allowed (was `E_VIEW_GROUP_TINT_UNUSABLE`) |
| `hierarchy`, `none` | none | `E_VIEW_GROUP_TINT_UNUSABLE` remains |

Scale resolution, `E_PRESENTATION_SCALE_*` diagnostics, paint completion and contrast gating are unchanged; only the scale source label for a field-less grouping is the grouping dimension.

## Files and tests

- `src/chrona/presentation/contracts/resources.py` (the contract check), `src/chrona/usecases/render_review.py` (source label), `docs/specification/50-constraint-driven-gantt-surface-quality.md` (Group tint paragraph), `schemas/common-v0.1.schema.yaml` (description only).
- `src/chrona/resources/presets/library.yaml`: `target-b` references `designs/target-b/*` in place with the shared `design-default` View; the design uses no icon catalogue, so the entry lists none.
- Tests: `tests/integration/test_group_tint.py` (objectType tint; `none` still rejected), `tests/integration/test_design_presets.py` (list/copy/render for `target-b`), CLI golden updated for the listing.
- Evidence: `tools/regenerate_public_examples.py --check` passes for all 46 public slides, including HALCYON `21-target-b`.
