<!-- chrona:literal-acceptance/v1 -->

# Release Review — Minimal `chrona init` and Explicit Corpus Example (#376)

## Literal issue acceptance

### Issue #376

- Source: [Issue #376](https://github.com/tya5/chrona/issues/376)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona init` produces a tree a newcomer can read end to end, whose README describes their project. | met | [minimal template](../../../src/chrona/resources/templates/minimal); [init tests](../../../tests/unit/chrona/usecases/test_local_authoring.py) | — |
| 2 | The full example remains available behind an explicit flag. | met | [CLI parser](../../../src/chrona/app/cli.py); [installed-wheel smoke](../../../tools/wheel_smoke.py) | — |
| 3 | No generated closure sits beside hand-edited source. | met | [initializer](../../../src/chrona/usecases/local_authoring.py); [all-Context Store test](../../../tests/unit/chrona/usecases/test_local_authoring.py) | — |
| 4 | A guide shows the smallest working project and the render command for it. | met | [first-project guide](../../guides/first-project.md); [documented-command gate](../../../tools/check_documented_commands.py) | — |

## Programme-level criteria (optional)

The default starter has only `project.yaml`, `actual.yaml`, and `README.md`.
Its documented command uses #377's package-owned default preset to produce a
Draft SVG.  `--example halcyon-1` retains the corpus and keeps its immutable
revision closure below `.chrona/store`.  Registry-published `baseline:`
snapshots and Context closure revisions route through their respective local
Store adapters without a mutable-source fallback.

## Architecture conclusion

The feature separates user-editable Draft source from reproducible corpus
source and Store runtime state.  Template selection remains in local-authoring,
package lookup remains in `chrona.resources`, draft presentation selection
remains #377's resolver, and materialization/Scene ownership are unchanged.
