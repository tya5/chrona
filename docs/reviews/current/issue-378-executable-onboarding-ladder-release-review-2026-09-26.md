<!-- chrona:literal-acceptance/v1 -->

# Release Review — Executable Onboarding Ladder (#378)

## Literal issue acceptance

### Issue #378

- Source: [Issue #378](https://github.com/tya5/chrona/issues/378)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona init demo && chrona render demo/project.yaml -o demo.svg` produces a chart of two tasks and one gate. | met | [starter](../../../src/chrona/resources/templates/minimal/project.yaml); [CLI test](../../../tests/cli/test_cli.py) | — |
| 2 | Appending a task to `demo/project.yaml` and re-running changes the output. | met | [append/render test](../../../tests/integration/test_onboarding_tutorial.py) | — |
| 3 | Each Project feature in the tutorial renders from its own snippet. | met | [progressive guide](../../guides/progressive-project-tutorial.md); [fixture test](../../../tests/integration/test_onboarding_tutorial.py) | — |
| 4 | `chrona render demo/project.yaml --preset <each shipped preset> -o out.svg` succeeds for every shipped preset. | met | [five-preset CLI test](../../../tests/cli/test_cli.py); [catalogue](../../../src/chrona/resources/presets/library.yaml) | — |
| 5 | A five-line Theme with `extends` plus two overridden tokens renders and differs visibly from its base. | met | [five-line source](../../../examples/aster-ssd/themes/onboarding-variation.yaml); [render test](../../../tests/integration/test_render.py) | — |

## Programme-level criteria (optional)

The [first-project guide](../../guides/first-project.md) leads from `init` to
render, preset copy, and bounded Theme inheritance. The progressive guide
then executes seven independent Draft stages and three advanced immutable
corpus commands. The last stage adds an Actual Set and a View explicitly
selecting progress. Scenario, snapshot and extension are demonstrated through
their real Project/View/Context/package owners, not misrepresented as a
default-View Project-only edit. The documented-command gate executes every
listed command in a disposable workspace; public materializer reproduction
checks advanced SVG and Scene bytes.

The Theme resolver checks both exact source bytes and the canonical complete
base, recurses within the same immutable snapshot, and emits only an ordinary
v0.11 Theme to the closure. The implementation deliberately does not add View
inheritance or arbitrary YAML merging. The
[5b909ce8 CI matrix](https://github.com/tya5/chrona/actions/runs/36207540414)
passed Ubuntu, macOS, Windows, newest-Python reproduction and wheel smoke.
The rejection and ordinary-source-identity tests added at 01bea1cd and this
review commit are subject to the final CI observation before issue closure.

## Architecture conclusion

Project and Actual Set own source facts; View owns scenario/progress
selection; Context and snapshot reader own immutable baseline and extension
closure; Theme inheritance resolves at ingress. Layout, Scene, and adapters
remain unchanged by tutorial syntax. The guide follows these boundaries and
does not introduce a second rendering pipeline.
