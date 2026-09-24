# Issue #372 — Executable Guides Release Review

**Decision:** Accept and close

## Requirement audit

| Requirement | Evidence | Result |
| --- | --- | --- |
| Bounded documentation input | The checker discovers only logical `chrona` invocations inside fenced blocks, including `$ ` prompts and continuations; prose and inline generated-reference forms are excluded. | Pass |
| Local, accountable skips | An adjacent `chrona:doc-check skip` marker applies only to the next command-bearing block; empty, malformed, unattached, and command-free markers fail. | Pass |
| Safe execution | The executor runs argv vectors without a shell in a temporary workspace containing a copied corpus; source examples and checkout outputs cannot be changed by normal documented paths. | Pass |
| Correct command identity | The executor resolves the console entry point from the active Python installation's scripts directory, rather than accepting an unrelated PATH shim. | Pass |
| Existing guides classified | 19 fenced invocations are discovered: 5 execute and 14 have precise local reasons for requiring author-owned assets, state, or immutable references. | Pass |
| Working curriculum command | `example-curriculum.md` now renders `scale-30.yaml` with executive inputs and actuals.  A disposable execution produced an SVG with 30 planned marks and measured `2357` height. | Pass |
| Reverse command surface | `cli-reference.md` remains an argparse-generated exact report checked for freshness; it is intentionally not recursively treated as an authored executable example. | Pass |
| CI enforcement | The conformance workflow invokes `tools/check_documented_commands.py --check --execute` on every supported OS. | Pass |

## Verification evidence

- Focused documented-command and Draft rendering tests: **27 passed**.
- Static and runtime documentation checks: **passed**.
- Conformance, module reachability, Scene delivery, View dispatch, import
  direction, text encoding, diagnostic/declared-value inventory, and init
  template checks: **passed**.
- Public materializer reproduction: **22 passed**; generated SVG diff empty.
- Full parallel suite: **727 passed, 17 skipped**.
- Built wheel: `chrona-0.1.0a0-py3-none-any.whl`, **2,374,019 bytes**;
  forced installed-wheel smoke outside the checkout: **passed**.  Editable
  development installation was restored before the final documentation check.
- GitHub Actions [run 36012337420](https://github.com/tya5/chrona/actions/runs/36012337420)
  passed Ubuntu, macOS, and Windows, including the new runtime documentation
  command, conformance, full pytest, and wheel smoke.

## Architecture conclusion

Documentation verification remains tooling: it consumes Markdown and invokes
the public CLI, but it neither imports use cases nor changes product command,
storage, Context, materializer, or rendering authority.  The copied fixture
boundary preserves immutable corpus evidence, while explicit skips state where
author-owned state is genuinely required.  The independent argparse-derived
reference keeps complete public surface visibility without letting generated
documentation masquerade as a runnable user journey.
