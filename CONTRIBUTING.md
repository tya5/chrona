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

Manual, when changing Layout allocation: run `.venv/bin/python tools/check_draft_viewport_matrix.py --jobs 4` (add `--cli` to exercise the saved-Context command). Every case must render or give its recorded exact refusal; capacity cases remain linked to #1490. The gallery freshness check already runs in conformance CI.

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

### Native typesetter checks

Run the opt-in `typesetter-compile` workflow (manual dispatch, or the
`typesetter-compile` PR label) for the implicit default and every
builtin preset. It pins Typst 0.15.1 and Tectonic 0.17.0, verifies release archive
checksums and executable versions, then compiles original exports without
rewriting them. The retained artifact contains source, logs, PDFs and a typed
`report.json`; refusals are not successful compiles. Locally use
`.venv/bin/python tools/check_typesetter_compile.py --help` and a fresh output
directory. The tool supplies bundled fonts through Typst's font path and a
private Fontconfig configuration for TeX on Linux. macOS Tectonic uses native
font discovery instead and may reject the same source when its font families
are not installed; the tool preserves that failure, rather than installing
system fonts or claiming portable font closure. Compiler success alone does not
establish exact font metrics; inspect the PDFs and font warnings too.

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
