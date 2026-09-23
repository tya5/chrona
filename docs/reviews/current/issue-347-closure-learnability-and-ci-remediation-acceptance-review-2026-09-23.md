# Issue #347 Closure Learnability and CI Remediation Acceptance Review

**Status:** Accepted  
**Date:** 2026-09-23

## Delivered remediation

| Concern | Result |
| --- | --- |
| Lost schema explanation at the closure boundary | `ClosureError` retains its stable ID and source reference while carrying optional detail; the CLI publishes that detail without changing the exception-string contract. |
| Schema annotation claim | Corrected before implementation: conditional branch descriptions are the author-facing unit, while nested applicator snippets are validator mechanics. The existing live gate and focused structural traversal test cover the valid boundary. |
| Duplicate CI work and cold dependencies | Push runs are limited to `main`; checkout returns to shallow default; pip cache is keyed by `pyproject.toml`. Ubuntu/macOS matrix, concurrency cancellation, gate order, and `pytest -n 4` remain intact. |
| #322 decision record | A closure comment records that Specification 58's accepted evidence-model alternative, rather than the proposed source-tree split, resolved the issue. |

## Verification

- Focused CLI, closure, and annotation tests: `39 passed`.
- Conformance and all four structural gates: passed.
- Parallel full suite: `464 passed, 7 skipped`.
- Public materializer suite: `11 passed`; generated SVG diff is empty.
- Wheel build, isolated installed-wheel smoke, and restored editable development install: passed.

## Architecture conclusion

Diagnostics now preserve the existing three-part public contract—ID, pointer,
and explanation—without sending validator types beyond the closure boundary.
The annotation correction avoids treating implementation fragments as a second
authoring vocabulary.  CI changes reduce duplicated work without weakening
platform coverage, reproducibility evidence, or test isolation.
