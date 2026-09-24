# Issue #355 — Corpus Coverage Implementation Plan

**Implements:** `issue-355-corpus-coverage-design-2026-09-24.md`

## C355-1 — Pure inventory model

Create `tools/corpus_coverage.py` with pure loaders/discovery, explicit
register-probe predicates, finite-schema vocabulary discovery, and canonical
Markdown rendering. Inputs are repository-relative declared corpus resources
only; no rendering or package/network lookup is allowed.

**Files:** tool, unit tests under `tests/unit/tools/` or the established tool
test location.

**Acceptance:** minimal fixtures prove each probe, negative undeclared
resources do not count, and identical input produces identical bytes.

## C355-2 — Publication and stale-report interface

Add CLI arguments `--root`, `--output`, and `--check`; use atomic output for
normal generation. Generate `docs/examples/corpus-coverage.md` from main's
four corpus projects and link it from the policy guide/docs navigation as
needed.

**Acceptance:** generated report has lexical ordering and evidence paths;
`--check` succeeds for committed output and has a stable failure for stale
output. No CI workflow treats absent coverage as a failing threshold.

## C355-3 — Release evidence

Run focused tool tests and `--check`, then public materializer reproduction of
every declared slide, full pytest, conformance and structural gates, installed
wheel smoke, generated SVG audit, and GitHub CI. Review the generated Markdown
as documentation and SVGs as one batched evidence set.

**Acceptance:** report is current, all existing gates remain green, and #355
is closed with links to the design, implementation, and release evidence.
