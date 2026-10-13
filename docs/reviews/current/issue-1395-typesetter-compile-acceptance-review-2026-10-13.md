<!-- chrona:literal-acceptance/v1 -->

# Issue 1395 native compiler gate

## Literal issue acceptance

### Issue #1395

- Source: [Issue #1395](https://github.com/tya5/chrona/issues/1395)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | the compile job exists and passes for the default and every exportable preset; documented engine versions; failures are typed. | met | [Native CI38357185387](https://github.com/tya5/chrona/actions/runs/38357185387) succeeds on6f2f366a: artifact11793805724 independently confirms18/18 compiled default/catalogue target cases, zero errors/refusals, plus6 synthetic native cases. [Runner and typed-negative tests](../../../tests/unit/tools/test_check_typesetter_compile.py), [opt-in job](../../../.github/workflows/typesetter-compile.yml), [versions/setup](../../../CONTRIBUTING.md#native-typesetter-checks). | — |

## Programme-level criteria (optional)

The compiled default Typst and Linux TikZ PDFs were rasterized and inspected:
one page, canvas, table, marks, labels, routes and legend present. Synthetic
SVG/Typst/TikZ pattern output at0/45/90 degrees was compared as one batch.
Compilation is not exact font
metric fidelity. Source artifacts were never patched. No authored examples
or Scene/Layout ownership changes. Product authority:d5f6418f; successful
native evidence head:6f2f366a. Final current-head PR checks and exact-main
three-OS release containing this acceptance disposition remain mandatory
before deliberate issue closure.

## Architecture conclusion

Adapters correct target grammar only; compiler execution, private font search,
typed failures and retained evidence remain tooling/CI responsibilities.
