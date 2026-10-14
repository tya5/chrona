# Issue #1338 PDF CFF acceptance review

<!-- chrona:literal-acceptance/v1 -->

Design: [work record](https://github.com/tya5/chrona/issues/1338#issuecomment-6157441073),
[Spec08 §2.3](../../specification/08-scene-and-rendering.md#23-pdf-font-outline-translation-1338),
published87c7f849 and correction3c517f7a. Implementation83f75cd9; READY base85ed35f1.

## Literal issue acceptance

### Issue #1338

- Source: [issue](https://github.com/tya5/chrona/issues/1338)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A role resolving to a CFF installed face renders to PDF, with the glyphs of the resolved face (a synthetic CFF test fixture, no host font). | met | [Actual PDF integration](../../../tests/integration/test_pdf_cff_installed.py):12 cases across CFF/CFF2/default-variable/nonzero TTC face and A/H/AH text; injected installed-font directory only. It extracts actual embedded FontFile2, checks original human family, retained glyph coordinates and widths against exact converted source, PDF text and source digest; repeated same-family subsets cannot reuse another payload. [Helper tests](../../../tests/unit/chrona/presentation/renderers/test_pdf_fonts.py) cover exact index, default instance, deterministic aliases, retained metrics/mappings, versioned permissions and untouched sources. | — |
| 2 | Output without installed CFF faces is byte-identical. | met | Controller-Z public PDF render before/after: exact `cmp` success, SHA2564905061695bdb8bf2d7ea86e4a1ece0762f15150f82749735e41e4201b488eba (ReportLab5.0.1/svglib2.2.0). Non-CFF registration/map/identity branch unchanged; PNG/SVG serialization unchanged. [Existing target tests](../../../tests/unit/chrona/presentation/renderers/test_target_registry.py) and installed-font tests included in70PASS batch. Current-head CI snapshot remains required for public artifacts. | — |

## Architecture and release

The adapter consumes completed family/weight and exact font closure, never measures
or selects a fallback. A strict render-local public svglib map connects registered
faces; pre-name payload digests namespace registration and PostScript identities.
Permissions concern selected faces, not unselected TTC siblings. No private
ReportLab font-state/configuration mutation, source rewrite, Scene/Layout change
or new runtime dependency. pypdf is dev-only, for actual embedded-glyph verification.
Luna whole-code review found no architecture blocker; helper/map/real-PDF42PASS,
combined target/installed/helper/map/real-PDF70PASS. Full local suite is not duplicated.
PR1480 head801e08d7 passed CI38489908947; artifact11860839050 retained all101
members/all92 Scene+SVG bytes. [Exact-main release38491118717](https://github.com/tya5/chrona/actions/runs/38491118717)
on READY1299e952 passed full pytest/conformance/wheel on all three OSes,
MCP floor and newest-Python public materializers. Both literal rows are met;
issue1338 is closed. Final helper/map/actual-PDF43 tests include actual unused
CFF registration, retaining one real source cmap anchor without substitution.

## Programme-level criteria (optional)

None.
