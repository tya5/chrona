# Issue #372 — Executable Guides Architecture Review

**Decision:** Accept design

## Boundary audit

| Boundary | Decision | Result |
| --- | --- | --- |
| Markdown → documentation tool | A bounded fence parser belongs in `tools/check_documented_commands.py`; Markdown is not a product input format. | Preserved |
| Documentation tool → CLI | The runner invokes the installed public command using parsed vectors; it does not import use cases or emulate behavior. | Preserved |
| CLI → product use cases | No command grammar, error semantics, or implementation ownership changes. | Preserved |
| Fixture → corpus | `examples/` is copied into a temporary directory; documented runs cannot mutate committed corpus evidence. | Preserved |
| Static grammar → runtime execution | Both consume one fenced-command discovery result; argparse remains the only grammar authority. | Preserved |
| Generated reference → authored guides | `cli-reference.md` remains generated from argparse, while authored guide examples are inputs to the reverse coverage check. | Preserved |

## Whole-system consistency

Chrona's immutable Context/materializer path remains the only route for public
evidence.  The runner exercises Draft and local authoring examples merely as
documentation behavior; it does not create Contexts, relax identity rules, or
make a temporary render reproducible evidence.  The `init`/`materialize` block
uses its own temporary project, so its declared output verification remains
real while its source is disposable.

Skip markers are deliberately documentation metadata rather than a CLI flag or
schema annotation.  They make an externally-required asset or author-created
state visible without pretending it can be fabricated.  A local attachment
rule prevents broad or accidental exemption, and static argparse validation
continues to reject stale syntax even for a skipped block.

The design adds no presentation, Layout, Scene, scheduling, storage, or
materializer responsibility.  It therefore needs ordinary regression and
public-materializer byte checks, not new renderer fixtures or compatibility
paths.

## Rejected alternatives

- Running arbitrary fenced shell: would make CI a shell interpreter for prose
  and create platform-dependent authority outside the CLI.
- Rewriting documented paths for a fixture: would test a different command
  from the one a reader sees.
- Treating every illustrative example as runnable by synthesizing resources:
  would hide its required author-owned inputs and bypass the immutable
  reference boundary.
- Removing reverse CLI coverage once runtime checking exists: runtime success
  cannot reveal a newly shipped, undocumented command or option.
