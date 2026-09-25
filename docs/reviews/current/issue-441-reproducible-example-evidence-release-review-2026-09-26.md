<!-- chrona:literal-acceptance/v1 -->

# Release Review — Reproducible Example Evidence and Reachability (#441)

## Literal issue acceptance

### Issue #441

- Source: [Issue #441](https://github.com/tya5/chrona/issues/441)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | None of the listed paths exists. | met | [ASTER topology](../../../examples/aster-ssd); [reachability test](../../../tests/unit/tools/test_check_example_reachability.py) | — |
| 2 | The README hero image is a file some manifest regenerates, and a check fails if it is not. | met | [README](../../../README.md); [reachability checker](../../../tools/check_example_reachability.py) | — |
| 3 | No file under `examples/` is unreachable from a manifest or context without a recorded reason. | met | [supporting-file reasons](../../../examples/reachability.yaml); [reachability checker](../../../tools/check_example_reachability.py) | — |

## Programme-level criteria (optional)

The root README directly references ASTER's manifest-declared
`generated/overview.svg`. The strict gate traverses typed local closure
references, checks every declared generated artifact exists, and permits the
small non-materializer population only through reasoned entries.

## Architecture conclusion

Manifest and Context remain the ownership roots for renderable example source
and evidence. README has no preview cache; it points at the same SVG that the
public materializer checks. The repository-quality graph observes this
topology without gaining rendering authority.
