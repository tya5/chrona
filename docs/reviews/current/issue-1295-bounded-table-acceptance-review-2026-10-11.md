<!-- chrona:literal-acceptance/v1 -->

# Bounded table acceptance (#1295)

[Current design, architecture and implementation record](https://github.com/tya5/chrona/issues/1295#issuecomment-6094464024). Authority: Specs24 section2.1, 33 sections6/8, 50 section3.1. Packaged migration: `8ca3aa79`.

## Literal issue acceptance

### Issue #1295

- Source: [Issue #1295](https://github.com/tya5/chrona/issues/1295)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test with one title far longer than the canvas. From the Scene, the table's inline extent stays within the declared bound and the plot keeps the rest. The long title's cell has more than one line (or an ellipsis plus a diagnostic). No `W_LAYOUT_VISIBLE_OVERFLOW` for the title. | met | [All packaged preset Scene/SVG tests](../../../tests/integration/test_packaged_bounded_table.py) and [bounded render tests](../../../tests/integration/test_bounded_table_render.py) cover long title/cell wrapping, source-linked ellipsis, share ceiling, retained plot and no title overflow; actual View YAML supplies the intent. | — |
| 2 | The same project with short titles produces the same Scene as today. | met | [Packaged fitting-copy tests](../../../tests/integration/test_packaged_bounded_table.py) compare whole SceneSurface and SVG bytes with only the new wrap/share declarations absent; every library preset passes. Truthful migrated resource identities are separate from unchanged geometry/paint/routes/diagnostics. | — |
| 3 | Do not edit `examples/**`. | met | [Packaged implementation](https://github.com/tya5/chrona/commit/8ca3aa79): `git diff --name-only origin/main...HEAD -- examples` is empty for authored work. | — |

## Programme-level criteria (optional)

Release pending: final trusted READY integration, public artifact/identity migration disposition, current schema gate and PR checks, then review-containing exact-main three-OS release. No closure is authorized by these local rows.

Packaged/default, all-nine live-View and bounded-render batch: 23 passed (20.95s).
Schema-equivalence passed against `e19005d0`: nine Layout and one reference-View
version-migration deltas, live View additions, four known-invalid fixtures
unchanged (L2+L3=38.7s). Pre-integration public audit: all46 materializers pass,
Scene/SVG bytes unchanged. Ordinary integration of the published #1293/#1294
WIPs preserves both policies; 45 date-range/bounded-preset tests passed (18.13s)
and three precise corpus-mirror guards passed (4.29s). Typed parsing retains
both endpoint and wrapping fields by keyword. Final integration schema/artifact
and release gates remain pending. A baseline gate label that already overflowed
is not fitting-copy evidence: opt-in ellipsis changes it intentionally.

## Architecture conclusion

View normalizes closed wrap intent once; Layout closes immutable source facts at each actual candidate width, honors authored minima, applies the declared share, measures heading independently and emits completed lines/ellipsis with source diagnostics. Scene/adapters never allocate or measure. Existing budgets/closure serve fixed, flexible and Grid hosts; no project-specific conditional, font reduction or plot-label policy was introduced. Preserve the independent #1294 axis migration during final integration.
