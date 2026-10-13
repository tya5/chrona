<!-- chrona:literal-acceptance/v1 -->

# Issue 1395 native compiler gate

## Literal issue acceptance

### Issue #1395

- Source: [Issue #1395](https://github.com/tya5/chrona/issues/1395)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | the compile job exists and passes for the default and every exportable preset; documented engine versions; failures are typed. | not met | [Selected design and baseline](https://github.com/tya5/chrona/issues/1395#issuecomment-6139338268); [runner](../../../tools/check_typesetter_compile.py), [opt-in job](../../../.github/workflows/typesetter-compile.yml), [version/setup instructions](../../../CONTRIBUTING.md#native-typesetter-checks). Focused tests: 49 passed. Native macOS matrix: eight Typst cases compiled; eight TikZ cases failed missing font families; technical-print refused on both targets pending pattern support. Linux gate and rendered TikZ evidence remain required. | — |

## Programme-level criteria (optional)

The compiled default Typst PDF was rasterized and inspected: one page, canvas,
table, marks, labels, routes and legend present. Compilation is not exact font
metric fidelity. Source artifacts were never patched. No authored examples
or Scene/Layout ownership changes. No release acceptance claim yet.

## Architecture conclusion

Adapters correct target grammar only; compiler execution, private font search,
typed failures and retained evidence remain tooling/CI responsibilities.
