# Issue #555 — CI paths work record

## Published baseline and design plan

Public `main` at start: `20cf279d6e483da693d7dc803f359d1da8fe854c`.
The current workflow runs conformance, full pytest, and wheel smoke on all
three OSes for every PR and `main` push. PR #484's measured run was about
13 minutes. Issue #526 requires the acceptance-review-bearing `main` commit's
own green CI; #452's throughput design preserves full release evidence.
No product schema, rendering, or materializer bytes change in this issue.

### Literal acceptance

- [ ] A doc-only PR finishes CI in about 3 minutes or less, and still fails when an acceptance review is malformed. Test this with a PR that breaks the review heading.
- [ ] A code PR's CI wall-clock time is at most about half of today's (about 13 min), with pytest sharded on ubuntu, and a failing test in any shard fails the run.
- [ ] Push to `main`, nightly and manual runs still execute the three-OS matrix with conformance, full pytest and wheel smoke. A deliberately OS-specific failure is caught there.
- [ ] `tools/check_ci_outcomes.py` and the independent-outcome reporting work for both paths.
- [ ] `AGENTS.md` describes the two paths, and states that issue closure cites the three-OS `main` run of the acceptance commit.

### Design questions and sequence

The CI workflow owns event routing; a small testable helper owns PR path
classification. Unknown paths or diff failures must select the code path.
Decide the narrow documentation allowlist, deterministic and exhaustive
three-way pytest distribution, independent outcome reporting, and a safe
OS-specific failure probe. Review against #526's exact-main release rule and
the cross-platform release expectations in specifications 62 and 64.

Publish in order: (1) this baseline and design plan; (2) selected design and
whole-architecture review; (3) implementation plan; (4) workflow, helper,
tests, and contributor guidance; (5) acceptance review with live CI evidence.
Each publication uses a separate commit and a checked remote base.
