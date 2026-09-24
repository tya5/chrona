# Executable Guides Design (#372)

## Decision

Documentation command verification has two independent directions:

1. **Forward:** every logical `chrona` invocation in a fenced Markdown block
   either executes with exit status zero in a disposable fixture workspace or
   is explicitly skipped with a local reason.
2. **Reverse:** the live argparse command/option surface remains rendered into
   `docs/guides/cli-reference.md` and is checked against the documented command
   population.

The existing `tools/check_documented_commands.py` owns both documentation
parsing and static argparse validation.  It gains a small Markdown fence parser
and an optional executor; no runtime product module receives documentation or
filesystem-fixture behavior.

## Document contract

A candidate is a logical line in a fenced block whose first non-prompt text is
`chrona `; a console prompt may be `$ chrona `.  Backslash continuations form
one invocation and are tokenized with `shlex`.  Other shell text is not
executed, and inline prose is outside this contract.  This keeps the executor
from becoming a general shell runner.

An immediately preceding marker applies to exactly the next fenced block:

```html
<!-- chrona:doc-check skip: <non-empty reason> -->
```

The parser rejects an empty reason, a marker not followed by a fenced block,
and a marker attached to a block with no Chrona invocation.  A skipped block is
still statically checked against argparse.  A block with an invocation and no
marker must execute all of its Chrona invocations in source order.

## Fixture execution boundary

The executor creates one temporary workspace for a complete check.  It copies
the repository `examples/` tree into that workspace, sets it as the current
directory for each direct `chrona` subprocess, and leaves the source checkout
unwritable by commands.  Commands in one block run in order so the documented
`init` then `materialize` pair retains its stated relationship; independent
blocks share only disposable fixture state.

The executor uses parsed argument vectors, a fixed timeout, and the installed
`chrona` entry point.  It captures stdout/stderr and reports document-relative
path, first source line, command, exit status, and output on failure.  It does
not invoke a shell, expand environment variables, evaluate substitutions, or
rewrite documented arguments.  A documentation example must therefore either
be truthful and runnable against the copied corpus/temporary outputs or state
why it needs an author-owned input or state.

## Documentation classification

| Surface | Disposition |
| --- | --- |
| Controller Z plan-only and executive Draft renders | Execute against copied `examples/`; outputs remain temporary. |
| README `init` then `materialize` | Execute in order in the temporary workspace. |
| 30-row curriculum render | Add and execute the complete known-good command, including the executive View, Actual Set, `1600xauto`, and a temporary output. |
| Snapshot/Render Context/authoring revision examples | Skip: they require an author-created immutable reference or local workspace state not present in a generic fixture. |
| Icon and font import examples | Skip: they require an author-provided licensed/local input asset. |
| Generic `project.yaml` render examples | Skip: their names intentionally stand for author-owned resources, not corpus fixtures. |

## Static grammar and generated reference

The fence parser is the sole discoverer for authored command examples.  Each
discovered command is validated against the live argparse parser before
execution.  `cli-reference.md` is a separate reverse report generated
exclusively from that parser; its byte freshness proves every live command and
option is named, without making the generated report recursively satisfy an
authored-example coverage gate.  A skipped authored command still cannot hide
stale syntax.  The runtime executor is invoked explicitly in CI, rather than
making a report-generation command have side effects by default.

## Error vocabulary

Tool failures remain maintainer diagnostics and include a deterministic
document-relative anchor:

| Condition | Tool diagnostic |
| --- | --- |
| invalid/unattached skip marker | `E_DOCUMENTED_COMMAND_SKIP` |
| malformed shell tokens | `E_DOCUMENTED_COMMAND_SHELL` |
| invalid CLI grammar | existing `E_DOCUMENTED_COMMAND_*` diagnostic |
| missing console executable | `E_DOCUMENTED_COMMAND_EXECUTABLE` |
| non-zero/timed-out invocation | `E_DOCUMENTED_COMMAND_EXECUTION` |

No product diagnostic code or CLI behavior changes.

## Acceptance

- Fenced-block discovery, skip attachment, execution isolation, and failure
  provenance have focused tests.
- The curriculum guide contains the actual executable 30-row render command.
- All current README/guide command blocks are either executed or carry a
  truthful local skip reason.
- CI executes the documentation runner and preserves generated reverse CLI
  reference checking.
- Full regression, conformance, public materializer bytes, wheel smoke, and
  three-platform CI confirm no product behavior changed.
