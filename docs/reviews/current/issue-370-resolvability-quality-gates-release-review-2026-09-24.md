# Issue 370 resolvability quality gates release review

## Result: accepted pending GitHub CI

| Issue 370 acceptance requirement | Direct evidence |
| --- | --- |
| Diagnostic population and ingress actionability | `tools/diagnostic_inventory.py --check`, committed `docs/diagnostics/inventory.md`, exact bare-code policy, and focused negative tests. |
| Declared versus computed classification | `tools/declared_value_inventory.py --check`, nine classified rows, live producer command validation, and focused negative tests. |
| Public producers for pinned values | `chrona identity bytes|document`; focused CLI tests prove raw-byte versus canonical-document semantics; workspace revision remains the separate bookkeeping resolver. |
| Documented command validity | `tools/check_documented_commands.py --check`; nested-command, unknown-option/value, and undocumented-surface negative tests; generated CLI reference covers every live public option. |
| Executable first run | Built-wheel install followed by installed `chrona init` and `chrona materialize` succeeds through `tools/wheel_smoke.py`. |
| Corpus scale | `tools/corpus_coverage.py --check`, semantic magnitude table, declared threshold policy, and focused magnitude test. |
| Template portability | Packaged template drift check and built-wheel smoke prove init does not depend on a source checkout. |

## Local release evidence

- Conformance and all structural checks passed.
- Core unit suite: 385 passed.
- CLI/tools/materializer focused suite: 104 passed.
- Acceptance and integration suite: 243 passed, 17 skipped.
- Built wheel installed into the virtual environment; installed-wheel smoke
  passed outside the checkout.
- Generated reports were regenerated and `--check` verified them current;
  no generated-report diff remained.

## Architecture conclusion

The gates remain repository evidence only.  They do not create product-runtime
policy, alter immutable identity assertion semantics, make documentation an
evaluation input, or add a presentation-layer dependency.  The fresh-wheel
failure discovered during the gate was corrected through packaged application
resources, not a source-path fallback.

GitHub CI is the final three-operating-system acceptance evidence.
