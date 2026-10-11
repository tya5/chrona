# Contributing to Chrona

Chrona is design-first. A change that alters semantics, ownership, a public schema,
or a compatibility promise must update the living specification or add an ADR before
implementation begins. Pure fixes and mechanical refactors must still cite the design
they preserve.

## Development setup

Run from the repository root. CI executes this same recipe in a fresh venv:

<!-- contributor-setup -->
```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,render]' -e packages/chrona-fonts-noto-cjk
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
Keep the venv in this checkout: editable installs otherwise import another
worktree. The local CJK provider is required by this unit-suite setup.

For a quick pre-push check (add the focused tests for your change):

```bash
.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_presentation_labels.py tests/unit/tools/test_yaml_loader_policy.py
```

This is a smoke loop, not the full unit, integration, CLI, MCP, corpus or
conformance gate. CI's PR shards exclude `corpus` tests; the three-OS release
matrix runs all tests. To run the unit suite explicitly:

```bash
.venv/bin/python -m pytest tests/unit -n 4
```

Optional MCP tests additionally need `.venv/bin/python -m pip install -e '.[mcp]'`.
Use `.venv/bin/python conformance/run_conformance.py` for conformance.

### Public evidence checks

Reachability and ledger tests require current manifest-declared generated
SVG/Scene files. A source PR must not commit generated files or managed reports.
For an intentional corpus change, use a disposable worktree (and its own venv),
then run these expensive checks together:

```bash
.venv/bin/python -m tools.derived_evidence --write
.venv/bin/python -m pytest tests/acceptance/output tests/integration -k 'ledger or corpus or reachab or inventory or coverage' -n 8
```

Do not edit sources while derivation runs: it renders a snapshot copied at
start, so subsequent edits make its output stale. Review the generated diff,
but publish only authored inputs. Keep the disposable worktree for inspection
instead of resetting a checkout containing other changes. CI regenerates the
same evidence for the PR. A new slide's ledger test prints the missing row;
copy that row into `tests/acceptance/output/public-slide-ledger.yaml` only after
checking that the rendered result is intended, then rerun the ledger test.

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
