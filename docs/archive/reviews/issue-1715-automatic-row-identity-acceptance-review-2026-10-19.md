<!-- chrona:literal-acceptance/v1 -->

# Automatic-row identity warning acceptance

## Literal issue acceptance

### Issue #1715

- Source: [Issue #1715](https://github.com/tya5/chrona/issues/1715)
- Observed: 2026-10-19

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Decide whether an automatic-mode View with no `tableColumns` should get default columns (for example the row title) or a pointed diagnostic, so that no bar is left unidentifiable. | met | [Reviewer decision](https://github.com/tya5/chrona/issues/1715#issuecomment-6252778918): a pointed warning, not synthesized columns or a refusal. Pre-code Spec50 `3077d7bde`; [published design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1715#issuecomment-6252829087). | — |
| 2 | Show the decision on a synthetic twin with 20+ crowded rows and its PNG. | met | [24-row fixture and actual SVG tests](../../../tests/integration/test_automatic_row_identity.py), [no-column PNG](assets-1715/automatic-no-column.png), [title-column PNG](assets-1715/automatic-title-column.png). Actual PNGs are 450×1170: existing canvas growth and ellipsis are unchanged; unique Task00–23 name prefixes are readable on every columned row. | — |
| 3 | a synthetic twin with 20+ crowded rows gives exactly one such warning with the count and the fix; the same twin with `tableColumns: [title]` gives none, and its PNG shows every row named. | met | [Paired rendering/transport assertions](../../../tests/integration/test_automatic_row_identity.py): one `W_LAYOUT_ROW_IDENTITY_MISSING:count=24`, pointing at `/body/tableColumns` with title-column/wider-plot-or-viewport remedies. Its formal title-column twin emits none; all24 distinct table names appear in SVG and inspected PNG. Existing24 per-label findings remain. The acceptance shorthand is not new YAML syntax; the fixture supplies all required column settings. | — |

## Architecture and focused evidence

Implementation `e11a59c76` joins normalized intent with accepted Layout facts
after count-trial selection and before passive Scene projection. A pure Layout
helper counts distinct ordinary row IDs through selected member source IDs,
without parsing drawing IDs or counting temporal absences. The alternative
`path` name is covered; delta-only content is not a name. Existing suppression
totals and per-label diagnostics remain. No geometry, defaults, schema,
adapter, authored example or project-specific rule changes. Independent
architecture review found no blocker or unnecessary new mechanism.

[Pure Layout tests](../../../tests/unit/chrona/presentation/layout/test_surface_row_identity.py)
cover row deduplication, intent gates and a real temporal-only completion.
New and adjacent render/message tests pass40; the added path-name case brings
the new unit/integration batch to10 passes. Accepted-count/render-plan tests
pass13. Import direction and Layout float-accumulation guards pass.

PNG reproduction: call the integration fixture's `_render(directory,
columns=False|True)` to create each synthetic resource bundle, then use
`chrona render project.yaml --view view.yaml --theme theme.yaml --scheme
scheme.yaml --layout layout.yaml --viewport 450x600 --visual-profile
chrona-output/visual/v0.5-baseline --format png --output result.png`.
Actual CLI JSON has exactly one aggregate warning for no-column and none for
title-column. Both PNGs are byte-identical to their pre-change render controls;
the warning does not repaint or resize the figure.

## Programme-level criteria (optional)

Initial [PR run39150249147](https://github.com/tya5/chrona/actions/runs/39150249147)
had one failing test: the new Layout module was missing from Spec33's ownership
table. The table and required ownership docstring are corrected; the guard
is unchanged. Both other pytest shards, conformance and reproduction passed;
derived-ready failed downstream of that test. Its snapshot's 50 SVGs and
50 Scenes were byte-identical; only diagnostic inventory source positions
changed. This initial old-base run is not final release evidence.

Final head `20a54dbc2166e2bd1cf41172bb746385828ee700` passed
[PR CI39153184816](https://github.com/tya5/chrona/actions/runs/39153184816).
[Official artifact12146280959 audit](https://github.com/tya5/chrona/pull/1735#issuecomment-6253444867)
confirms all50 SVGs and50 Scenes byte-identical; only diagnostic inventory
source positions move. PR1735 merged at `12b5adb22`.

Exact review-containing ready main
`ee4f8593854f569f45d9b419c0aaceafead5a635` passed
[release39155086049](https://github.com/tya5/chrona/actions/runs/39155086049):
Windows/Linux/macOS full pytest, conformance and wheel/smoke, MCP floor and
newest-Python public reproduction all succeed. The issue is
[closed with all three literal rows accepted](https://github.com/tya5/chrona/issues/1715#issuecomment-6254134683).
