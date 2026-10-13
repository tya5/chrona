<!-- chrona:literal-acceptance/v1 -->

# Issue 1395 native compiler gate

## Literal issue acceptance

### Issue #1395

- Source: [Issue #1395](https://github.com/tya5/chrona/issues/1395)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | the compile job exists and passes for the default and every exportable preset; documented engine versions; failures are typed. | not met | [Selected design and baseline](https://github.com/tya5/chrona/issues/1395#issuecomment-6139338268); [runner](../../../tools/check_typesetter_compile.py), [opt-in job](../../../.github/workflows/typesetter-compile.yml), [version/setup instructions](../../../CONTRIBUTING.md#native-typesetter-checks). Focused155 tests pass; six synthetic native pattern cases pass. [Linux baseline38355719227](https://github.com/tya5/chrona/actions/runs/38355719227) artifact11792528494 has16 compiled cases and only2 technical-print refusals (incomplete, not accepted). Current pattern implementation exports both technical-print targets and compiles Typst. The final18-case Linux matrix and containing-review release remain required. | — |

## Programme-level criteria (optional)

The compiled default Typst and Linux TikZ PDFs were rasterized and inspected:
one page, canvas, table, marks, labels, routes and legend present. Synthetic
SVG/Typst/TikZ pattern output at0/45/90 degrees was compared as one batch.
Compilation is not exact font
metric fidelity. Source artifacts were never patched. No authored examples
or Scene/Layout ownership changes. No release acceptance claim yet.

## Architecture conclusion

Adapters correct target grammar only; compiler execution, private font search,
typed failures and retained evidence remain tooling/CI responsibilities.
