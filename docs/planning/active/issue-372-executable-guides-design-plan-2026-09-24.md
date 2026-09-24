# Design Plan: Executable Guides (#372)

**Status:** Proposed

## Objective

Make every documented `chrona` invocation in a fenced command block of the
README or a user guide either execute successfully in an isolated fixture
workspace or carry an explicit, local reason why it cannot execute unattended.
Add the proven 30-row curriculum command to its guide.  Preserve the inverse
CLI-surface report so new public commands and options cannot become invisible.

## Verified starting point

- `tools/check_documented_commands.py` discovers command-looking lines across
  README and guides, validates their tokens against argparse, and generates
  `docs/guides/cli-reference.md`; it neither understands Markdown fences nor
  runs commands.
- `docs/guides/example-curriculum.md` describes
  `examples/controller-z/curriculum/scale-30.yaml` and `1600xauto`, but has no
  invocation that renders it.
- Existing fenced command examples include runnable corpus renders, a chained
  `init`/`materialize` example, and deliberately illustrative commands whose
  files, immutable references, local authoring state, or licensed fonts cannot
  exist in an unattended checkout.
- The product CLI is deterministic over explicit files.  Documentation
  execution must therefore use a disposable current directory and may read
  repository fixtures, but must never write to source examples or alter a
  developer's checkout.

## Design questions

1. Define a fenced-block parser that identifies only shell-like blocks and
   logical `chrona` invocations (including `$ ` prompts and continuations),
   without treating prose or inline code as executable.
2. Define a block-local `chrona:doc-check skip` marker grammar, attachment
   rule, and non-empty-reason validation so a skip cannot silently cover a
   neighboring block.
3. Define the fixture workspace: temporary working directory, read-only
   access to declared repository examples, command ordering within a block,
   output isolation, environment normalization, timeout/error reporting, and
   prohibited shell interpretation.
4. Decide which existing examples become executable and which gain honest skip
   reasons; avoid replacing an invalid illustrative command with a different
   undocumented command.
5. Preserve static argparse validation and the generated reverse CLI surface
   reference as a separate check; define how static and runtime diagnostics
   name document path, line, and block.
6. Review the design against CLI/use-case boundaries, corpus immutability,
   portable installed-wheel behavior, generated-document ownership, and the
   existing documentation quality gates.

## Planned outputs

1. English design and whole-architecture review.
2. An implementation plan containing parser/annotation, fixture executor,
   documentation migration, reverse-report preservation, and release-gate
   slices.
3. Focused parser/executor tests, the working curriculum command, full
   documentation execution, full regression, and three-platform CI evidence.

## Exit criteria

- The design states a single source of truth for command grammar (the live
  argparse parser), a bounded Markdown annotation syntax, and a non-mutating
  execution model.
- Every existing fenced documented invocation is classified as runnable or
  explicitly skipped with a truthful reason.
- The curriculum's exact 30-row command is executable from the guide.
- Static reverse coverage remains generated and checked independently of
  runtime execution.
