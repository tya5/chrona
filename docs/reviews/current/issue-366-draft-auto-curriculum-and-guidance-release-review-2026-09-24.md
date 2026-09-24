# Issue 366 release review

- #364 post-hoc review required no change.
- #365 follow-up now states the complete `layoutIntent` removal, publishes a
  runnable 30-row Draft YAML, and documents `WIDTHxauto` in README and CLI help.
- Draft overflow keeps its command hint; immutable Context overflow now directs
  authors to `environment.viewport.blockSize` and rematerialization.
- Unsupported Draft auto surfaces report `surface=<name>`.
- Focused render/CLI tests pass, including public fixture output and immutable
  Context guidance characterization. Full CI is the final release gate.
