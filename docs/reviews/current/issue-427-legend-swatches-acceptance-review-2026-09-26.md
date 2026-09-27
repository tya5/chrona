<!-- chrona:literal-acceptance/v1 -->

# Release Review — Legend Swatches and Arrangement (#427)

**Reviewed product:** `16064c81` on `main` (branch commit `f8e97c64`) (I427-1). **Design:** [design](../../design/issue-427-legend-swatches-design-2026-09-26.md), [amendment](../../design/issue-427-legend-swatches-design-amendment-2026-09-26.md), [architecture review](issue-427-legend-swatches-architecture-review-2026-09-26.md), Specifications 33 and 49. **Slice review:** [I427-1](issue-427-legend-swatches-i427-1-review-2026-09-26.md). **CI:** [four-job CI run 36252576297](https://github.com/tya5/chrona/actions/runs/36252576297) on `4de0e2ae`, green.

## Literal issue acceptance

### Issue #427

- Source: [Issue #427](https://github.com/tya5/chrona/issues/427) (merged from #422, closed as a duplicate)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A milestone legend entry renders as the symbol the Theme binds for milestones, at the size the chart draws it. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): `test_legend_milestone_entry_renders_as_the_bound_symbol_at_chart_size` fails before this slice (swatch was `Rect`) and passes after; `halcyon-1/02-programme-board`'s `legend-swatch:milestone` is now `Symbol`, diamond, `10.0×10.0` (`planned`'s `markHeight` ratio × `timeline.mark.blockSize`), rendered and inspected. | — |
| 2 | An outline-only mark, a dashed line and a relation terminal each have a legend key that shows them. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): `test_legend_outline_pattern_role_swatch_has_no_fill`, `test_legend_as_of_entry_renders_as_a_dashed_stroke`, `test_legend_dependency_entry_renders_as_a_stroke_with_its_terminal` each fail before and pass after; `halcyon-1/03-launch-campaign`'s new legend (`planned` outline rect, `asOf` dashed stroke, `dependency` stroke with an arrowhead), rendered and inspected. | — |
| 3 | A layout profile can declare a horizontal legend, and one committed example renders one. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): `layout-profile-v0.9.schema.yaml`'s `legend` slot gains an optional `direction: inline`; `test_legend_inline_direction_flows_entries_left_to_right` fails before (field did not exist) and passes after; `halcyon-1/layouts/print-portrait.yaml` declares it and `03-launch-campaign` renders it. | — |
| 4 | No legend entry's appearance is decided by `surface_composer` arithmetic that a document cannot reach. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): every legend-swatch dimension now traces to the entry's own role's Theme tokens (`markHeight`/`markOffset`/`markCornerRadius`/`dash`/`strokeWidth`/`marker`/`pattern`), the new `legend-swatch.swatchInlineSize` Theme property, or the `legend` slot's `direction`/`gap`/`itemMinInlineSize` Layout Profile fields. The one remaining fixed constant is the explicit, documented compatibility fallback for an undeclared role or field (`test_legend_unrecognized_role_keeps_the_fixed_square_fallback`), not undeclarable policy. | — |
| 5 | A scale entry shows the entity's declared title when one exists. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): `test_scale_legend_entry_label_prefers_the_entitys_declared_title` fails before (raw field value) and passes after; `halcyon-1/02-programme-board`'s scale entries show `entities.*.title` (`Spacecraft bus`, …), ellipsized where narrow. | — |
| 6 | Swatch and label take separate theme roles. | met | [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md): `semantic_registry.py`: `legendEntry.theme_role = "legend-swatch"`, `legendLabel.theme_role = "legend"`; no swatch dimension reads the label's typography role after this slice (`swatch_geometry`/`emit_swatch` never call `text_treatment("legend")` for sizing, only `legend_size` for the documented legacy fallback and text placement itself). | — |

## Programme-level criteria (optional)

- Focused tests: 803 passed, 1 skipped (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`); `tests/acceptance`: 170 passed, 19 skipped (unrelated).
- Public materializers: `tools.regenerate_public_examples --write` then `--check`, 22/22 slides reproduce byte-for-byte against the newly written evidence. Every one of the 12 changed slides was structurally diffed against its pre-change evidence: zero non-legend primitive, bound, paint value, or diagnostic differs in any of them (see the [I427-1 review](issue-427-legend-swatches-i427-1-review-2026-09-26.md) for the full attribution, including the correction that the change's blast radius is wider than phase 1 estimated — every committed example with a `legend` slot, not only `halcyon-1`'s).
- Conformance: `conformance/run_conformance.py` — PASS, 32/32 checks.
- CI: [four-job CI run 36252576297](https://github.com/tya5/chrona/actions/runs/36252576297) on `4de0e2ae`, green.

## Architecture conclusion

Layout (`layout/surface_composer.py`) owns every legend-swatch geometry decision, dispatched by a closed table keyed on the entry's declared role and constructed with the same `MarkPlacement`/`ShapePlacement`/`RelationPlacement` types and geometry functions (`mark_geometry`, `symbol_geometry`'s shape vocabulary, relation marker resolution, `tokens.background`) real marks, relations and decorations already use. Scene (`scene/v05_builder.py`) only projects those placements through the same per-kind emission branches real marks/relations already have; it calculates no geometry. Theme (`theme-v0.11`) and Layout Profile (`layout-profile-v0.9`) each gained additive optional fields in place, per lead direction, with documented fallbacks that keep every undeclared legend byte-identical to before this change. View is untouched.

Out of scope, named rather than silently narrowed: `progressFill`/`summaryBar` legend roles fall to the historical fixed-square fallback rather than the `mark` bucket (no literal acceptance criterion or committed example needs them legended; a future issue can extend the closed dispatch table). `calendarClosed` is documented in the design as a future `decoration`-bucket case but is not exercised or specially handled by this slice's code (also falls to the fallback bucket today).

Release disposition: all six literal rows (four from #427, two merged from #422) are met.
