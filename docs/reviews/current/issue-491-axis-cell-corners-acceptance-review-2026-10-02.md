<!-- chrona:literal-acceptance/v1 -->

# Issue #491 — axis cell corners acceptance review

Source: [Issue #491](https://github.com/tya5/chrona/issues/491), observed 2026-10-02 (body unchanged since filing; the four comments are the implementing session's claim, owner decisions D1-D9 and two status blocks). The issue has one acceptance row, copied below. Design: [work record](../planning/active/issue-491-axis-cell-corners-2026-10-02.md) (baseline, design plan, design, architecture review, implementation plan), living contract [Specification 39](../../specification/39-axis-and-observation-clarity.md) "Axis cell corners (#491)".

Slices: design publication [PR #953](https://github.com/tya5/chrona/pull/953) (`faa76be5`); code [PR #956](https://github.com/tya5/chrona/pull/956) (`9c619a48`); committed slide [PR #957](https://github.com/tya5/chrona/pull/957) (`a474d425`), with the derived-sync evidence commit `d8b5b8fa`. Owner decisions (options, choice, why, reversal) are [a comment on the issue](https://github.com/tya5/chrona/issues/491#issuecomment-5953151391) and work record section 5.6.

## Literal issue acceptance

### Issue #491

- Source: [Issue #491](https://github.com/tya5/chrona/issues/491)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A band tier's Theme role can declare a corner shape (radius or chamfer) for its cells, and one committed slide shows it. | met | The band roles `axis-band-decoration` and `axis-band-decoration2` accept `cellCornerRadius` or `cellCornerChamfer`, named number tokens that are a ratio of the cell block size, `0 < ratio <= 0.5` ([`theme-v0.11`](../../../schemas/theme-v0.11.schema.yaml), [`theme-v0.13`](../../../schemas/theme-v0.13.schema.yaml), admitted in `scene/capabilities.py`). Layout ([`surface_axis.py`](../../../src/chrona/presentation/layout/surface_axis.py) `_cell_corner`, `_band_cell`) draws a rounded `Rect` (`corner_radius`) or a closed eight-point polygon inside the cell rect, carried by Scene as a `Symbol` outline; a corner wider than half a narrow cell is reduced and recorded as `W_LAYOUT_AXIS_CELL_CORNER_REDUCED`; both shapes, a ratio outside the range and a chamfer with a pattern are `E_PRESENTATION_AXIS_INVALID`. Every cell keeps its id, paint order, role and label host. 24 Layout and adapter tests in [`test_axis_cell_corners.py`](../../../tests/unit/chrona/presentation/scene/test_axis_cell_corners.py) (fixture font, expected outlines computed from each cell's own bounds: radius, chamfer, gap, abutting cells, first and last cell, per-role shapes, each error, narrow-cell reduction, Typst and TikZ) and 10 pipeline tests in [`test_axis_cell_corners_render.py`](../../../tests/integration/test_axis_cell_corners_render.py) (SVG `rx` and path, a resvg PNG probe at a cut corner and at the cell centre, perceptibility gates, host, schema accept and reject); no `examples/` input. 17 mutants killed, 0 survivors. Committed slide: Controller Z [`axis-cell-corners`](../../../examples/controller-z/generated/axis-cell-corners.svg) ([manifest entry](../../../examples/controller-z/manifest.yaml), [view](../../../examples/controller-z/views/axis-cell-corners.yaml), [Theme](../../../examples/controller-z/themes/axis-cell-corners.yaml), [context](../../../examples/controller-z/contexts/axis-cell-corners.yaml)): chevron-ended quarter cells (chamfer) over pill-ended month cells (radius), separated by a 4 px gap, labels inside their cells. Rendered and read (resvg PNG of the committed SVG, axis zoomed): corners lie inside the axis slot, the window-edge quarter cell keeps its outer cut, labels are clear of the rounded ends. `tools/check_scene_perceptibility.py` PASS (37 scenes, 0 errors). | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The Theme gained two optional role properties, in place (Specification 56 section 3.2); no View, Scene schema or adapter change. Layout owns the outline; Scene carries `corner_radius` or a `Symbol`; SVG, resvg and TikZ draw both. The occlusion gate now treats an opaque band `Symbol` cell as ground (roles read from the semantic registry), proven by a test that fails if that is dropped and by a test that other Symbols stay non-occluding. The default path is unchanged: `tools/regenerate_public_examples.py --check` was byte-identical for all 36 slides before the new one, and the slide PR changed no existing slide. S0 (`python -m tools.schema_equivalence --base-rev origin/main`): both Theme schemas gain two properties and no expected-delta entry; the standalone command reports earlier PRs' `values/additionalProperties/allOf` entries as "does not apply" against a base that already contains them (identical with the base set to this tree minus my diff), which I did not edit; the conformance `schema-equivalence` check passes.

Disclosures:

- **Typst.** A radius is drawn; a chamfer fails with `E_VISUAL_CAPABILITY_UNSUPPORTED` because the Typst adapter rejects every Scene `Symbol`. A Theme that declares a chamfer cannot be rendered through Typst until the adapter gains a polygon branch (decision D9). Searched open and closed issues (`typst polygon`, `chamfer`): no duplicate; not filed, as the row requires only SVG-class output.
- **Not delivered, by design and not filed:** per-side corners such as Off-World's tab with only the upper corners cut (additive `cellCornerSides`, D8), tier-end-only corners for a continuous band (additive `cellCornerScope`, D5), a catalogue pattern on a chamfered cell (D7). Searched (`per-side corner`, `cellCorner`, `tab corner axis`, `rounded corners axis`): none. Targets were read as pictures and READMEs only; no preset or catalogue Theme was edited, so neither Off-World's nor Sunday Strip's preset adopts a corner yet (a preset-owner decision).
- **Test-suite counts moved with the new slide** (as of its merge): 37 slides, 332 axis labels (7 new: 2 quarter, 5 month), 14 hosted DVT labels, 83 derived paths.
- **Process.** The first code push carried `docs/diagnostics/inventory.md`, a derived path the PR check rejects; a follow-up commit removed it and the derived snapshot regenerates it.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #491; record that run in the issue closing comment.
