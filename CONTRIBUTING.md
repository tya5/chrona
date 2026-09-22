# Contributing to Chrona

Chrona is design-first. A change that alters semantics, ownership, a public schema,
or a compatibility promise must update the living specification or add an ADR before
implementation begins. Pure fixes and mechanical refactors must still cite the design
they preserve.

## Development setup

```bash
python -m pip install -e '.[dev,render]'
pytest
python conformance/run_conformance.py
```

The CLI is the only documented stable programmatic entry point for the alpha release.
Internal Python modules may change until a public API is declared.

## Repository map

- `docs/specification/`: living normative design
- `docs/decisions/`: architectural decisions
- `schemas/`: public schema authorities
- `conformance/`: executable normative fixtures
- `src/chrona/`: implementation grouped by semantic owner
- `tests/unit/chrona/`: source-mirrored unit tests
- `tests/integration/`, `tests/cli/`, `tests/acceptance/`: cross-boundary evidence
- `examples/`: reproducible user-facing projects
- `tools/`: maintainer utilities

## Pull requests

Keep one concern per pull request. Include the design/specification impact, tests run,
and any migration note. Generated runtime resource mirrors under
`src/chrona/resources/` must remain byte-identical to their named root authorities.
Do not add a license or change licensing language without an explicit maintainer
decision.
