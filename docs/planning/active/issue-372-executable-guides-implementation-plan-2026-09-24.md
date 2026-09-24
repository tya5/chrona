# Implementation Plan: Executable Guides (#372)

**Status:** Proposed

**Implements:** [Issue #372 design](../../design/issue-372-executable-guides-design-2026-09-24.md)

## I372-1 — Bounded document model and static validation

Refactor `tools/check_documented_commands.py` to parse fenced blocks, logical
Chrona invocations, and adjacent skip markers into typed document records.
Validate each authored command against argparse and retain the separately
argparse-generated CLI-reference freshness check.  Reject malformed,
unattached, and reasonless skips.

**Files:** `tools/check_documented_commands.py`,
`tests/unit/tools/test_documented_commands.py`.

**Acceptance:** inline/prose text is excluded; prompts and continuations are
preserved; invalid marker attachment and stale syntax fail with anchored tool
diagnostics; the generated reverse CLI report remains fresh.

## I372-2 — Isolated executable-document runner

Add an explicit executor mode to the same tool.  It creates a temporary
workspace, copies corpus inputs, invokes only parsed `chrona` argv vectors in
source order with a bounded timeout, and reports path/line/stdout/stderr on
failure.  Wire this mode into the three-platform workflow after static
documentation validation.

**Files:** `tools/check_documented_commands.py`,
`tests/unit/tools/test_documented_commands.py`, `.github/workflows/conformance.yml`.

**Acceptance:** runner tests prove a successful fixture command, non-zero
diagnostics, skip non-execution, and no source-tree output; CI has an explicit
runtime documentation step.

## I372-3 — Authored guide migration and curriculum evidence

Add the known-good 30-row Controller Z command to
`docs/guides/example-curriculum.md`.  Annotate each non-runnable existing
fenced command block with a precise local skip reason; preserve runnable corpus
and init/materialize commands exactly.  Regenerate and check the reverse CLI
reference.

**Files:** `README.md`, affected `docs/guides/*.md`,
`docs/guides/cli-reference.md`.

**Acceptance:** every candidate block is executed or explicitly skipped;
curriculum command produces an auto-height 30-row SVG from copied corpus
inputs; no documentation command is rewritten to a different fixture command.

## I372-4 — Release gate

Run focused tool tests, static and runtime documentation checks, conformance,
structural gates, public materializer byte checks, full parallel pytest,
generated-document/SVG diff review, built-wheel smoke, and three-platform CI.
Publish a release review before closing #372.

**Acceptance:** all design acceptance criteria have direct evidence and the
runtime documentation runner is green on Ubuntu, macOS, and Windows.
