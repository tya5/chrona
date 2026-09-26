<!-- chrona:literal-acceptance/v1 -->

# Release Review — Independent Axis Name Tables (#432)

**Implementation:** `911c5e02cc870c0a5fc6c2e44f4778708277adfc` on `main`.
**Design authorities:** [design](../../design/issue-432-axis-name-table-design-2026-09-26.md),
[architecture review](issue-432-axis-name-table-architecture-review-2026-09-26.md),
[template correction](../../design/issue-432-axis-name-table-template-validation-correction-2026-09-26.md),
[month coincidence correction](../../design/issue-432-axis-name-table-partial-equivalence-correction-2026-09-26.md),
and [living specification](../../specification/63-axis-name-tables.md).

## Literal issue acceptance

### Issue #432

- Source: [Issue #432](https://github.com/tya5/chrona/issues/432)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Under `ja-JP`, a month tier can render `Jan`, `January`, `1月` and `01`; under `en-US` it can render `1月`. | met | [Five public-SVG render cases](../../../tests/integration/test_materialize_example.py), [View selection and default tests](../../../tests/unit/chrona/presentation/review/test_v05_content.py), and [packaged tables](../../../src/chrona/resources/axis-name-tables-v0.1.yaml). | — |
| 2 | No two distinct month forms produce the same string under the same table without that being reported. | met | [Validated exact coincidence closure](../../../src/chrona/presentation/model/axis_names.py), [catalog audit](../../diagnostics/axis-name-tables.md), [negative catalog tests](../../../tests/unit/chrona/presentation/model/test_axis_names.py), and placed-alias `W_LAYOUT_AXIS_FORM_EQUIVALENT` coverage in [Scene tests](../../../tests/unit/chrona/presentation/scene/test_v05_builder.py). | — |
| 3 | No axis label path branches on a language code. | met | [Table-driven Layout formatter](../../../src/chrona/presentation/layout/axis.py), [structural test](../../../tests/unit/chrona/presentation/layout/test_presentation_axis.py), and [single selected table for auto-fit and final placement](../../../src/chrona/presentation/layout/surface_composer.py). | — |

## Programme-level criteria (optional)

The View contract advances to v0.22; v0.21 is no longer runtime ingress.
`label.nameTable` is optional and defaults to the Render Context locale's exact
packaged table. The five SVG cases use a Japanese-capable Theme; this keeps
font coverage distinct from vocabulary selection. No host locale, system
catalog, or adapter-side name substitution is involved.

## Verification and artifact review

- Focused unit/integration run: **166 passed**, 46 existing `jsonschema.RefResolver`
  deprecation warnings. This includes five materialized SVG output cases.
- `python conformance/run_conformance.py`: **PASS** across all checks, including
  catalog audit, schema inventories, import direction, and public coverage.
- `python tools/regenerate_public_examples.py --check --jobs 4`: **PASS**, 21
  slides. All 21 committed SVGs are byte-identical to the previous revision.
  All 21 Scene payloads are unchanged after removing `provenance`; changed
  Scene bytes record the new View identity only. Thus there is no visible
  raster delta to inspect in the committed corpus.
- Public Controller Z English and Japanese Views explicitly demonstrate the
  `nameTable` declaration; source Views and Context pins migrate atomically
  with v0.22. No unrelated geometry or paint change was found.
- [Implementation CI](https://github.com/tya5/chrona/actions/runs/36219775255):
  **PASS**. Windows, macOS, and Ubuntu each passed full pytest, conformance,
  wheel/smoke and independent-outcome gates. Newest-Python public-materializer
  reproduction also passed.

## Architecture conclusion

View selects a finite table identity; Context locale supplies only its
default. The validated packaged catalog owns names and format templates.
Layout owns formatted text, measured fit, and placement; Scene projects
completed primitives, and adapters serialize them. Coincidence declarations
are validated against all twelve months, including English May's partial
short/long equivalence. This closes the #408 vocabulary gap without restoring
locale-dependent branching or introducing Scene/adapter policy.
All three literal criteria are met; #432 is ready to close after this review
commit is published and its release gate is confirmed.
